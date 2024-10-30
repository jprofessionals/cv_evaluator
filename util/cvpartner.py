import requests
from datetime import datetime
from util.cvpartner_user import CVPartnerUser


class CvPartner:
    base_url = 'https://jpro.cvpartner.com/api/'

    def __init__(self, api_key, logger, cv_output_path):
        self.api_key = api_key
        self.logger = logger
        self.cv_output_path = cv_output_path

    def get_users(self) -> dict[str, CVPartnerUser]:
        session = requests.Session()
        session.headers.update({'Authorization': f'Bearer {self.api_key}'})
        session.headers.update({'Content-Type': 'application/json'})

        response = session.get(f'{self.base_url}v1/countries')
        if response.status_code != 200:
            self.logger.error(f'Failed to retrieve countries: {response}')
            raise Exception(f'Failed to retrieve countries: {response}')

        body = response.json()

        office_ids = []
        company = body[0]
        for office in company['offices']:
            office_ids.append(office['id'])

        self.logger.info(f"found the following office ids: {office_ids}")
        office_ids_str = ', '.join(['"{}"'.format(value) for value in office_ids])

        search_param = f"""
        {{
          "office_ids": [{office_ids_str}],
          "offset": 0,
          "size": 100
        }}
        """

        response = session.post(f'{self.base_url}v4/search', data=search_param)
        if response.status_code != 200:
            self.logger.error(f'Failed to retrieve users: {response}')
            raise Exception(f'Failed to retrieve users: {response}')

        body = response.json()
        cvs = body['cvs']

        users = {}
        for cv in cvs:
            name = cv['cv']['name']
            is_deactivated = cv['cv']['is_deactivated']
            if is_deactivated:
                self.logger.info(f"user {name} is deactivated")
                continue
            user_id = cv['cv']['user_id']
            cv_id = cv['cv']['id']
            email = cv['cv']['email']
            updated_at = cv['cv']['updated_at']
            updated_dt = datetime.strptime(updated_at, '%Y-%m-%dT%H:%M:%S.%fZ')
            users[email] = CVPartnerUser(user_id, name, email, cv_id, updated_dt)

        return users


    def download_cv(self, username, the_user_id, the_cv_id) -> str:
        resp = requests.get(
            f"{self.base_url}v1/cvs/download/{the_user_id}/{the_cv_id}/no/pdf",
            headers={'Authorization': f'Bearer {self.api_key}'}
        )
        if resp.status_code != 200:
            self.logger.error(f'Failed to download CV for {username}: {resp}')
            raise Exception(f'Failed to download CV for {username}: {resp}')
        cv_filename = f"{self.cv_output_path}/{username}.pdf"
        with open(cv_filename, "wb") as out:
            out.write(resp.content)
        return cv_filename
