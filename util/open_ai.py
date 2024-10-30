import time

import openai


class MyOpenAI:
    def __init__(self, assistant_id):
        self.assistant_id = assistant_id

    def check_status(self, run_id,thread_id):
        run = openai.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id,
        )
        return run.status

    def evaluate_cv(self, pdf_filename) -> str:
        # create a thread
        thread = openai.beta.threads.create()
        thread_id = thread.id

        prompt = "hvordan oppfyller denne vedlagte CV'en kravene ? Bruk filen som er vedlagt. Hvis du ikke kan lese filen, svar kun 'feilet'"

        my_file = openai.files.create(
            file=open(pdf_filename, "rb"),
            purpose='assistants'
        )

        fileid = my_file.id

        # create a message
        message = openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=prompt,
            attachments=[{"file_id": fileid, "tools": [{"type": "file_search"}]}]
        )

        # run
        run = openai.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=self.assistant_id
        )

        run_id = run.id

        status = self.check_status(run_id, thread_id)
        while status != "completed":
            status = self.check_status(run_id, thread_id)
            time.sleep(2)

        ai_response = openai.beta.threads.messages.list(thread_id=thread_id)

        if ai_response.data:
            result_text = ai_response.data[0].content[0].text.value
            return result_text
        else:
            return ""
