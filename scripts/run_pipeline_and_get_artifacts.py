"""Start a pipeline on a project and retrieve the archived artifacts."""
import os
import zipfile
from time import sleep

import requests


def start_pipeline(project_id, api_token, ref='master'):
    """Start the gitlab pipeline and return the json response if successful."""
    response = requests.request(
        method='POST',
        url=f'https://gitlab.com/api/v4/projects/{project_id}/'
            f'pipeline?ref={ref}',
        headers={'PRIVATE-TOKEN': api_token})
    if response.status_code == 201:
        return response.json()
    else:
        raise requests.HTTPError(response.json())


def wait_for_pipeline(project_id, pipeline_id, api_token, timeout=10800):
    """Wait for pipeline to succeed or fail (wait while running or pending)."""
    wait_time = 20
    while timeout > 0:
        pipeline = requests.request(
            method='GET',
            url=f'https://gitlab.com/api/v4/projects/'
                f'{project_id}/pipelines/{pipeline_id}',
            headers={'PRIVATE-TOKEN': api_token}).json()
        print(f'Pipeline {pipeline_id} current status is {pipeline["status"]}')
        if pipeline['status'] in ['pending', 'running']:
            sleep(wait_time)
            timeout -= wait_time
        else:
            break
    # Assert that the pipeline did complete
    if pipeline['status'] not in ['failed', 'success']:
        # The job may have been cancelled or entered some other unexpected
        # state
        raise AssertionError(
            f'Pipeline had unexpected status {pipeline["status"]}')
    return pipeline


def retry_pipeline(project_id, pipeline_id, api_token):
    """Restart the specified pipeline."""
    response = requests.request(
        method='POST',
        url=f'https://gitlab.com/api/v4/projects/{project_id}/'
        f'pipelines/{pipeline_id}/retry',
        headers={'PRIVATE-TOKEN': api_token})
    if response.status_code == 201:
        return response.json()
    else:
        raise requests.HTTPError(response.json())


def get_pipeline_jobs(project_id, pipeline_id, api_token):
    """Get all the jobs associated with a pipeline."""
    return requests.request(
        method='GET',
        url=f'https://gitlab.com/api/v4/projects/{project_id}/'
            f'pipelines/{pipeline_id}/jobs',
        headers={
            'PRIVATE-TOKEN': api_token}).json()


def deploy_job_success(project_id, pipeline_id, deploy_job_name, api_token):
    """Return True if the the named deploy job succeded."""
    jobs = get_pipeline_jobs(project_id, pipeline_id, api_token)
    for job in jobs:
        if job['name'] == deploy_job_name and job['status'] == 'success':
            return True
    return False


def get_job_artifacts(project_id, job_id, api_token):
    """Get the job artifacts and unzip them in the current directory."""
    response = requests.request(
        method='GET',
        url=f'https://gitlab.com/api/v4/projects/{project_id}/'
            f'jobs/{job_id}/artifacts',
        headers={'PRIVATE-TOKEN': api_token})
    if response.status_code == 200:
        zipped_data = response.content
        filename = f'project-{project_id}-job-{job_id}-artifacts.zip'
        print(f'Fetched archive {filename}')
        with open(filename, 'wb') as output:
            output.write(zipped_data)
        zip_file = zipfile.ZipFile(filename)
        for name in zip_file.namelist():
            uncompressed = zip_file.read(name)
            with open(name, 'wb') as f:
                f.write(uncompressed)
                print(f'Found and extracted {name} in {filename}')


if __name__ == '__main__':
    # Grab the project, access token, name of the "deploy" job,
    # and the desired branch to run the pipeline on from the environment.
    project_id = os.environ.get('PROJECT_ID')
    api_token = os.environ.get('GITLAB_API_TOKEN')
    deploy_job_name = os.environ.get('DEPLOY_JOB_NAME')
    branch_ref = os.environ.get('PIPELINE_BRANCH_NAME', 'master')
    if not project_id:
        raise AssertionError(
                'You must provide the project id to run the pipeline in'
            )
    if not api_token:
        raise AssertionError(
                'You must provide avalid gitlab api token to start the'
                ' pipeline'
            )
    if not deploy_job_name:
        raise AssertionError(
                'You must provide the name of the deploy job to retry if it'
                ' fails.'
            )

    # Start the pipeline
    pipeline = start_pipeline(project_id, api_token, ref=branch_ref)
    # Wait for the pipeline to finish. Any failed tests will cause it to be
    # marked as "failed", so this is a reasonable terminal state.
    pipeline = wait_for_pipeline(
        project_id=project_id,
        pipeline_id=pipeline['id'],
        api_token=api_token)

    # If the deploy job failed, the whole pipeline failed.
    # in that case, we should try one more time to deploy and run pipeline.
    if not deploy_job_success(
            project_id,
            pipeline['id'],
            deploy_job_name,
            api_token):
        print(
            f'Deploy job {deploy_job_name} was not successfull, retrying...')
        # Retry the pipeline
        retry_pipeline(project_id, pipeline['id'], api_token)
        # Wait for the pipeline to complete
        pipeline = wait_for_pipeline(
            project_id=project_id,
            pipeline_id=pipeline['id'],
            api_token=api_token)

    # Grab the jobs that were in the pipeline
    jobs = get_pipeline_jobs(
        project_id=project_id,
        pipeline_id=pipeline['id'],
        api_token=api_token)

    # Download and extract the artifacts for each job
    for job in jobs:
        get_job_artifacts(project_id, job_id=job['id'], api_token=api_token)
