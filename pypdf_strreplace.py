#!/usr/bin/env python3
import pypdf
from typing import Any, Dict, Tuple, Union, List, cast
from pypdf.generic import DictionaryObject, NameObject
from pypdf.generic._base import TextStringObject, ByteStringObject, NumberObject, FloatObject
from pypdf.constants import PageAttributes as PG
from pypdf._cmap import build_char_map
import re

# from https://github.com/hoehermann/pypdf_strreplace/
# Copyright (c) 2006-2008, Mathieu Fenniak
# Some contributions copyright (c) 2007, Ashish Kulkarni <kulkarni.ashish@gmail.com>
# Some contributions copyright (c) 2014, Steve Witham <switham_github@mac-guyver.com>
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

class ExceptionalTranslator:
    def __init__(self, map):
        self.trans = str.maketrans(map)

    def __getitem__(self, key):
        if key not in self.trans.keys():
            error_message = f"Replacement character »{chr(key)}« (ordinal {key}) is not available in this document."  # error message on separate line to avoid confusion with the acutal string "key"
            raise ValueError(error_message)
        return self.trans.__getitem__(key)


class CharMap:
    def __init__(self, subtype, halfspace, encoding, map, ft):
        [setattr(self, k, v) for k, v in locals().items()]

    @classmethod
    def from_char_map(cls, subtype: str, halfspace: float, encoding: Union[str, Dict[int, str]], map: Dict[str, str],
                      ft: DictionaryObject):
        return cls(subtype, halfspace, encoding, map, ft)

    def decode(self, text: Union[TextStringObject, ByteStringObject]):
        # print("Decoding", text.get_original_bytes(), "with this map:")
        # pprint.pprint(self.map)
        if isinstance(self.encoding, dict):
            return str(text)  # it looks like pypdf applies the encoding dict automatically
        elif isinstance(text, TextStringObject) and self.encoding == "charmap":
            # decoding with ascii is a wild guess
            return "".join(text.get_original_bytes().decode('ascii').translate(str.maketrans(self.map)))
        elif isinstance(text, TextStringObject) and isinstance(self.encoding, str) and self.map:
            # it looks like utf-16 is decoded by pypdf but not quite, and I am confused and this is a total guess
            encoding = self.encoding
            if self.encoding == "utf-16-be":
                encoding = "utf-8"
            return "".join(text.get_original_bytes().decode(encoding).translate(str.maketrans(self.map)))
        elif isinstance(text, ByteStringObject):
            return "".join(text.decode(self.encoding).translate(str.maketrans(self.map)))
        else:
            raise NotImplementedError(
                f"Cannot decode {type(text)} „{text}“ with this {type(self.encoding)} encoding: {self.encoding}")

    def encode(self, text, reference):
        # print(f"Encoding „{text}“ to conform to", type(reference))
        if isinstance(self.encoding, dict):
            return TextStringObject(text)
        elif self.encoding == "charmap":
            map = {v: k for k, v in self.map.items()}
            return ByteStringObject(
                text.translate(ExceptionalTranslator(map)).encode('ascii'))  # encoding with ascii is a wild guess
        elif isinstance(reference, ByteStringObject):
            map = {v: k for k, v in self.map.items() if not isinstance(v, str) or len(v) == 1}
            return ByteStringObject(
                text.translate(str.maketrans(map)).encode(self.encoding))  # TODO: use ExceptionalTranslator here, too?
        else:
            raise NotImplementedError(f"Cannot encode this {type(self.encoding)} encoding: {self.encoding}")


# from https://github.com/py-pdf/pypdf/blob/27d0e99/pypdf/_page.py#L1546
def get_char_maps(obj: Any, space_width: float = 200.0) -> Dict[str, CharMap]:
    cmaps = {}
    objr = obj
    while NameObject(PG.RESOURCES) not in objr:
        # /Resources can be inherited sometimes so we look to parents
        objr = objr["/Parent"].get_object()
    resources_dict = cast(DictionaryObject, objr[PG.RESOURCES])
    if "/Font" in resources_dict:
        for font_id in cast(DictionaryObject, resources_dict["/Font"]):
            cmaps[font_id] = CharMap.from_char_map(*build_char_map(font_id, space_width, obj))
    return cmaps


class Context:
    def __init__(self, charmaps: Dict[str, CharMap], font: str = None):
        self.font = font
        self.charmaps = charmaps

    def clone_shared_charmaps(self):
        return type(self)(self.charmaps, self.font)


class PDFOperation:
    def __init__(self, operands, operator, context: Context):
        self.operands = operands
        self.operator = operator
        self.context = context

    @classmethod
    def from_tuple(cls, operands, operator, context: Context):
        operator = operator.decode('ascii')  # PDF operators are indeed ascii encoded
        classname = f"PDFOperation{operator}"
        if classname in globals():
            # create object of specific class
            return globals()[classname](operands, context)
        else:
            # create object of passthrough-class
            return cls(operands, operator, None)

    # ~ def __repr__(self):
    # ~ return self.operator
    def get_relevant_operands(self):
        return self.operands

    def write_to_stream(self, stream):
        for op in self.operands:
            op.write_to_stream(stream)
            stream.write(b" ")
        stream.write(self.operator.encode("ascii"))  # PDF operators are indeed ascii encoded
        stream.write(b"\n")


class PDFOperationTf(PDFOperation):
    def __init__(self, operands, context: Context):
        super().__init__(operands, "Tf", None)
        context.font = operands[0]


class PDFOperationTd(PDFOperation):
    def __init__(self, operands, context: Context):
        super().__init__(operands, "Td", None)
        self._infer_plain_text()

    def __str__(self):
        return f"{self.operands} {self.operator}"

    def _infer_plain_text(self):
        tx, ty = self.operands
        if ty != 0:
            # consider a vertical adjustment starting a new line
            ty.plain_text = "\n"
        elif tx != 0:
            # interpret horizontal adjustment as space. total guess. works for the xelatex sample.
            tx.plain_text = " "
        return map


class PDFOperationTJ(PDFOperation):
    def __init__(self, operands: list[list[Union[TextStringObject, ByteStringObject, NumberObject]]], context: Context):
        if len(operands) != 1:
            raise ValueError(f"PDFOperationTJ expects one non-empty Array of Array")
        super().__init__(operands, "TJ", context.clone_shared_charmaps())
        self._infer_plain_text()
        object_types = set([operand.__class__ for operand in operands]) - {NumberObject.__class__}
        if len(object_types) > 1:
            raise NotImplementedError(f"Cannot handle Operations with mixed string object types {str(object_types)}.")

    def __str__(self):
        return f"„{self.get_relevant_operands()}“ {self.operator}"

    def _infer_plain_text(self):
        for operand in self.get_relevant_operands():
            if isinstance(operand, NumberObject) or isinstance(operand, FloatObject):
                halfspace = self.context.charmaps[self.context.font].halfspace
                if operand < -halfspace:
                    # interpret big horizontal adjustment as space. total guess. works for the xelatex sample.
                    operand.plain_text = " "
            else:
                operand.plain_text = self.context.charmaps[self.context.font].decode(operand)

    def get_relevant_operands(self):
        return self.operands[0]

    def set_operand_text(self, text, index):
        sample = self.operands[0][index]  # use the operand which is going to be replaced as a sample
        # it is possible that the operand we are going to replace is a space produced by horizontal adjustment
        if not isinstance(sample, TextStringObject) and not isinstance(sample, ByteStringObject):
            # in this case, just select any text operand
            sample = next(
                (op for op in self.operands[0] if isinstance(op, TextStringObject) or isinstance(op, ByteStringObject)))
        self.operands[0][index] = charmaps[self.context.font].encode(text, sample)


class PDFOperationTj(PDFOperation):
    def __init__(self, operands: list[Union[TextStringObject, ByteStringObject]], context: Context):
        if len(operands) != 1:
            raise ValueError(f"PDFOperationTj expects one non-empty Array of TextStringObject")
        super().__init__(operands, "Tj", context.clone_shared_charmaps())
        self._infer_plain_text()

    def __str__(self):
        return f"„{self.get_relevant_operands()}“ {self.operator}"

    def _infer_plain_text(self):
        self.operands[0].plain_text = self.context.charmaps[self.context.font].decode(self.operands[0])

    def get_relevant_operands(self):
        return self.operands

    def set_operand_text(self, text, index):
        sample = self.operands[0]  # Tj has only one operand
        self.operands[0] = charmaps[self.context.font].encode(text, sample)


def append_to_tree_list(operations, tree_list):
    root = tree_list.GetRootItem()
    for operation in operations:
        if operation.__class__ == PDFOperation:
            continue  # only show operations relevant to text processing
        operation_node = tree_list.AppendItem(root, operation.operator)
        tree_list.SetItemText(operation_node, 3, str(getattr(operation, "scheduled_change", "")))
        for operand in operation.get_relevant_operands():
            operand_node = tree_list.AppendItem(operation_node, str(operand))
            tree_list.SetItemText(operand_node, 1, str(type(operand).__name__))
            tree_list.SetItemText(operand_node, 2, getattr(operand, "plain_text", "").replace(" ", "␣").replace("\n",
                                                                                                                "↲"))  # might also consider ␊ for visualising line breaks
            tree_list.SetItemText(operand_node, 3, str(getattr(operand, "scheduled_change", "")))
        if operation.operator in ["Td", "Tj", "TJ"]:  # only expand operators relevant to text
            tree_list.Expand(operation_node)
            tree_list.Expand(operand_node)


def extract_text(operations: List[PDFOperation]):
    text = ""
    for operation in operations:
        text += "".join([getattr(operand, "plain_text", "") for operand in operation.get_relevant_operands()])
    return text


class Change:
    def __str__(self):
        return self.__class__.__name__

    def apply(self, element=None, index=None, collection=None):
        pass


class Delete(Change):
    def apply(self, element=None, index: int = None, collection: List[Tuple] = None):
        collection.pop(index)


class Cluster(Change):
    def apply(self, element: Tuple = None, index: int = None, collection: List[Tuple] = None):
        element = collection.pop(index)
        target_index = next((i for i, e in enumerate(collection) if i >= index and e[1] == element[1]), None)
        if target_index is not None:
            collection.insert(target_index, element)


class Text(Change):
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return f"Set text to „{self.text}“"

    def apply(self, element=None, index=None, collection=None):
        element.set_operand_text(self.text, index)


def schedule_replacements(operations, matches, args_replace):
    text = ""
    match = None
    matches = matches[:]
    first_operation = None
    first_operand = None
    for operation in operations:
        for operand in operation.get_relevant_operands():
            if hasattr(operand, "plain_text"):
                previous_length = len(text)
                text += operand.plain_text
                while matches or match:
                    if match:
                        if len(text) >= match.end(0):
                            # we have enough text to cover the end of the current match
                            postfix = operand.plain_text[match.end(0) - previous_length:].strip("\n")  # see prefix
                            postfix = match.re.sub(args_replace, postfix) if args_replace else postfix  # see prefix
                            new_text = prefix + match.expand(
                                args_replace) + postfix if args_replace else prefix + match.group(0) + postfix
                            first_operand.scheduled_change = Text(new_text)
                            if operand != first_operand:
                                # the match spans multiple operands
                                # the first operand receives the replacement text in its entirety (with postfix)
                                # we do not need the current operand anymore. mark current operand for deletion
                                operand.scheduled_change = Delete()
                            # we changed an operand in the operation the match begun in
                            # this might be the current operation or a previous one
                            first_operation.scheduled_change = Change()
                            if operation != first_operation:
                                # the match spans multiple operations
                                # the first operations receives the replacement text in its entirety (with postfix)
                                # we do not need the current operations anymore. mark current operations for deletion
                                operation.scheduled_change = Delete()
                                if operation.operator in ["TJ"]:
                                    operand_changes = set([c.__class__.__name__ if c else c for c in
                                                           [getattr(op, "scheduled_change", None) for op in
                                                            operation.get_relevant_operands()]])
                                    if operand_changes - {Delete.__name__}:
                                        # print(f"But wait: Not all the operation's operands are going to be deleted! The operation must be changed, not deleted.")
                                        operation.scheduled_change = Change()
                            # reset text gathering metadata for next match
                            match = None
                            first_operation = None
                            first_operand = None
                        else:
                            # match exists, but the current text does not reach the end
                            # quit looking here and get more text
                            break
                    if matches:
                        if len(text) > matches[0].start(0):
                            match = matches[0]
                            matches.pop(0)
                            # newlines do not actually occur in the PDF. they have been added by us for visual representation. they must be removed here
                            prefix = operand.plain_text[:match.start(0) - previous_length].strip("\n")
                            # one operand might contain multiple matches. since we are focussing on the current match, we must re-do the search and replace in the prefix
                            prefix = match.re.sub(args_replace, prefix) if args_replace else prefix
                            first_operation = operation
                            first_operand = operand
                        else:
                            # match exists, but the current text does not reach the start
                            # quit looking here and get more text
                            break
            if (operation.operator in ["TJ", "Tj"] and first_operand is not None and not hasattr(operand,
                                                                                                 "scheduled_change")):
                # delete operands containing replaced text
                operand.scheduled_change = Delete()
        if first_operation is not None and not hasattr(operation, "scheduled_change"):
            # the match spans multiple operations
            # the current operation (might be Tf or something else entirely) did not contain any text and must be removed to avoid confusion
            operation.scheduled_change = Delete()
        if isinstance(getattr(operation, "scheduled_change", None), Delete) and operation.operator == "Td":
            # Td movement operations should not be deleted, but rather grouped together and moved behind the replacement
            operation.scheduled_change = Cluster()


def schedule_deletion(operations):
    """Schedule deletion of all text-related operations.

    Useful for redacting a document entirely while maintaining design."""
    for operation in operations:
        if operation.operator in ["TJ", "Tj", "Td", "Tf"]:
            operation.scheduled_change = Delete()


def replace_text(content, args_search, args_replace, args_delete):
    # transform plain operations to high-level objects
    operations = [PDFOperation.from_tuple(operands, operator, context) for operands, operator in content.operations]

    # flatten mappings into one plain text string
    text = extract_text(operations)

    matches = []
    if args_search:
        # search in text
        matcher = re.compile(args_search)
        matches = list(matcher.finditer(text))
    elif not args_delete:
        # just print
        print("# These are the lines this tool might be able to handle:")
        print(text)

    if args_delete:
        schedule_deletion(operations)
    else:
        # look up which operations contributed to each match and schedule to replace them
        schedule_replacements(operations, matches, args_replace)

    # visualize content stream structure and scheduled changes

    if args_replace or args_delete:
        # do the replacements, but working backwards – else the indices would no longer match
        # we iterate over the list of high-level operations, but we modify the pypdf low-level operations
        for operation_index, operation in reversed(list(enumerate(operations))):
            operation_change = getattr(operation, "scheduled_change", None)
            if operation_change:
                operation_change.apply(index=operation_index, collection=content.operations)
                if isinstance(operation_change, Delete):
                    # print(f"Deleted: {operation}")
                    pass
                elif isinstance(operation_change, Cluster):
                    # print(f"Moving together: {operation}")
                    pass
                else:
                    # print(f"Before replacements: {operation}")
                    for operand_index, operand in reversed(list(enumerate(operation.get_relevant_operands()))):
                        operand_change = getattr(operand, "scheduled_change", None)
                        if operand_change:
                            operand_change.apply(operation, operand_index, operation.get_relevant_operands())
                    # print(f"After replacements:  {operation}")

    return len(
        matches)  # return amount of matches – which is hopefully the amount of replacements (mind the postfixes!)


def main_func(inputfile, outputfile, searches_and_replacements, delete):
    total_replacements = 0
    reader = pypdf.PdfReader(inputfile)
    writer = pypdf.PdfWriter()
    for page_index, page in enumerate(reader.pages):
        global charmaps
        global context
        charmaps= get_char_maps(page)
        context = Context(charmaps)
        contents = page.get_contents()
        # NOTE: contents may be None, ContentStream, EncodedStreamObject, ArrayObject
        if isinstance(contents, pypdf.generic._data_structures.ArrayObject):
            for search,replace in searches_and_replacements:
                for content in contents:
                    total_replacements += replace_text(content, search, replace, delete)
        elif isinstance(contents, pypdf.generic._data_structures.ContentStream):
            for search,replace in searches_and_replacements:
                total_replacements += replace_text(contents, search, replace, delete)
        else:
            raise NotImplementedError(f"Handling content of type {type(contents)} is not implemented.")

        page.replace_contents(contents)
        writer.add_page(page)

    writer.write(outputfile)

    if searches_and_replacements:
        return total_replacements
    else:
        return 0
