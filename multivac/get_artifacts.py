#!/usr/bin/env python
import argparse
import glob
import os
import json
import requests


def cli_parser():
    parser = argparse.ArgumentParser(
        description='Download artifact zip archives from GitHub Actions. Needs'
                    '`fetch.py` first.'
    )
    parser.add_argument(
        '--repo-path', type=str, default='tarantool/tarantool',
        help='Owner/repository to get path to workflow run JSON files. '
             'Default tarantool/tarantool'
    )
    parser.add_argument(
        '--token-path', default='token.txt',
        help='Path to Personal Access Token, see more in "How to use" in README'
    )

    return parser.parse_args()


class BasicAuthToken(requests.auth.AuthBase):
    def __init__(self, token):
        self.token_file = token
        self.token = self.__get_the_token()

    def __call__(self, r):
        r.headers.update({
            'Accept': 'application/vnd.github.v3+json',
            'Authorization': f'token {self.token}',
        })
        return r

    def __is_token_valid(self):
        if not os.path.exists(self.token_file):
            raise RuntimeError(f'{self.token_file} is not exists')
        if not os.path.isfile(self.token_file):
            raise RuntimeError(
                f'{self.token_file} is not a regular file')
        return True

    def __get_the_token(self):
        assert self.__is_token_valid()
        with open(self.token_file, 'r') as f:
            token = f.read().strip()
        return token


class GitHubConnector:
    def __init__(self, token):
        self.session: requests.Session = requests.Session()
        self.session.auth = BasicAuthToken(token)
        self.timeout = 15

    def get_workflow_run_artifacts(self, artifacts_api_url):
        """
        Here we get response from GitHub REST API:
        If the result is OK, but there are no artifacts:
            status code: 200
            content:
                {'total_count': 0, 'artifacts': []}

        If the result OK and there are some artifacts:
            status code: 200
            the content see
            https://docs.github.com/en/rest/actions/artifacts?apiVersion=2022-11-28#list-workflow-run-artifacts

        If there are bad credentials:
            status code: 401
            content: {
                'message': 'Bad credentials',
                'documentation_url': 'https://docs.github.com/rest'
                }

        If the PAT rate limit exceeded:
            status code: 403
            content: {
                'message': "API rate limit exceeded for 10.10.10.10.
                (But here's the good news:
                Authenticated requests get a higher rate limit.
                Check out the documentation for more details.)",
                'documentation_url':
                'https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting'
                }
        """
        try:
            workflow_run_artifacts_data = self.session.get(artifacts_api_url,
                                                           timeout=self.timeout)
        except requests.exceptions.ReadTimeout:
            print(f"Connection timeout error to get artifacts data "
                  f"for {artifacts_api_url}")
            return []

        if workflow_run_artifacts_data.status_code == 200:
            return workflow_run_artifacts_data.json(
            ).get('artifacts', [])
        print(f'ERROR: Unable to get artifacts list: '
              f'{workflow_run_artifacts_data.text}')
        return None

    def get_artifacts(self,
                      artifact_archive_download_url: str):
        """
        If the download link is OK, we get response status code 200 and
        zip-archive as binary data in response content.
        If there is something wrong, we will get response status code 4xx.
        """
        try:
            download_response = self.session.get(artifact_archive_download_url,
                                                 timeout=self.timeout)
        except requests.exceptions.ReadTimeout:
            print(f"Connection timeout error to download artifacts archive for "
                  f"{artifact_archive_download_url}")
            return False
        if download_response.status_code != 200:
            print(f"WARN: Can't download artifact from "
                  f"{artifact_archive_download_url}. \n"
                  f"Response status code: {download_response.status_code}. \n"
                  f"Response text: {download_response.text}")
            return False
        return download_response


def get_workflow_run_artifact_base_data(workflow_run_file):
    with open(workflow_run_file, 'r') as f:
        run_json = json.load(f)
        artifacts_api_url = run_json.get('artifacts_url')
        workflow_run_id = run_json.get('id')
    return artifacts_api_url, workflow_run_id


if __name__ == '__main__':
    args = cli_parser()
    github = GitHubConnector(args.token_path)
    artifacts_dir = f'{args.repo_path}/artifacts'
    workflow_runs_dir = f'{args.repo_path}/workflow_runs'
    workflow_run_files = glob.glob(
        os.path.join(workflow_runs_dir, '*[0-9].json'))

    os.makedirs(artifacts_dir, exist_ok=True)

    for run_file in workflow_run_files:
        artifact_api_url, run_id = get_workflow_run_artifact_base_data(run_file)

        if not artifact_api_url:
            continue

        artifacts_list = github.get_workflow_run_artifacts(artifact_api_url)

        if artifacts_list is None:
            exit(1)
        if not artifacts_list:
            continue

        os.makedirs(f'{artifacts_dir}/{run_id}', exist_ok=True)

        for artifact in artifacts_list:
            path_to_file = f'{artifacts_dir}/{run_id}/{artifact["id"]}.zip'
            artifact_download_response = github.get_artifacts(
                artifact["archive_download_url"])

            if artifact_download_response:
                with open(path_to_file, 'wb') as f:
                    f.write(artifact_download_response.content)
