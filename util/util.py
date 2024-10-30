import logging
from cloudwatch import cloudwatch


def get_aws_logger(logger_name: str, log_group_name: str = "cvevaluator") -> logging.Logger:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(logger_name)

    formatter = logging.Formatter('%(asctime)s : %(levelname)s - %(message)s')
    handler = cloudwatch.CloudwatchHandler(log_group=log_group_name)

    handler.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger
