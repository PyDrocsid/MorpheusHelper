import requests


class Emekc:
    URL = "https://emkc.org/api/v1/piston/execute"

    @staticmethod
    def run_code(data: dict):
        return requests.post(Emekc.URL, data=data).text
