import json
from unittest.mock import Mock

from flask import g
import pytest

from dataactbroker import fileRoutes
from dataactcore.models.lookups import PUBLISH_STATUS_DICT
from tests.unit.dataactcore.factories.domain import CGACFactory
from tests.unit.dataactcore.factories.job import (JobFactory, SubmissionFactory)
from tests.unit.dataactcore.factories.user import UserFactory


@pytest.fixture
def file_app(test_app):
    fileRoutes.add_file_routes(test_app.application, Mock(), Mock(), Mock())
    yield test_app


def sub_ids(response):
    """Helper function to parse out the submission ids from an HTTP
    response"""
    assert response.status_code == 200
    result = json.loads(response.data.decode('UTF-8'))
    assert 'submissions' in result
    return {sub['submission_id'] for sub in result['submissions']}


def test_list_submissions(file_app, database, user_constants, job_constants):
    """Test listing user's submissions. The expected values here correspond to
    the number of submissions within the agency of the user that is logged in
    """
    cgacs = [CGACFactory() for _ in range(3)]
    user1 = UserFactory.with_cgacs(cgacs[0], cgacs[1])
    user2 = UserFactory.with_cgacs(cgacs[2])
    database.session.add_all(cgacs + [user1, user2])
    database.session.commit()

    submissions = [     # one submission per CGAC
        SubmissionFactory(cgac_code=cgac.cgac_code, publish_status_id=PUBLISH_STATUS_DICT['unpublished'])
        for cgac in cgacs
    ]
    database.session.add_all(submissions)

    g.user = user1
    response = file_app.get("/v1/list_submissions/?certified=mixed")
    assert sub_ids(response) == {sub.submission_id for sub in submissions[:2]}

    response = file_app.get("/v1/list_submissions/?certified=false")
    assert sub_ids(response) == {sub.submission_id for sub in submissions[:2]}

    response = file_app.get("/v1/list_submissions/?certified=true")
    assert sub_ids(response) == set()

    submissions[0].publish_status_id = PUBLISH_STATUS_DICT['published']
    database.session.commit()
    response = file_app.get("/v1/list_submissions/?certified=true")
    assert sub_ids(response) == {submissions[0].submission_id}

    g.user = user2
    response = file_app.get("/v1/list_submissions/?certified=mixed")
    assert sub_ids(response) == {submissions[2].submission_id}

def test_current_page(file_app, database, user_constants, job_constants):
    """Test listing user's submissions. The expected values here correspond to
    the number of submissions within the agency of the user that is logged in
    """
    #fails if only one of the two (EF) files exists, passes when both are present
    submission = SubmissionFactory(submission_id=1)

    jobA = JobFactory(submission_id=1, file_type_id=1, job_type_id=2, number_of_errors=0, file_size=123, job_status_id=4)
    jobB = JobFactory(submission_id=1, file_type_id=2, job_type_id=2, number_of_errors=0, file_size=123, job_status_id=4)
    jobC = JobFactory(submission_id=1, file_type_id=3, job_type_id=2, number_of_errors=0, file_size=123, job_status_id=4)
    jobD1 = JobFactory(submission_id=1, file_type_id=5, job_type_id=2, number_of_errors=0, file_size=123, job_status_id=4)
    jobD2 = JobFactory(submission_id=1, file_type_id=4, job_type_id=2, number_of_errors=0, file_size=123, job_status_id=4)
    jobE = JobFactory(submission_id=1, file_type_id=6, job_type_id=4, number_of_errors=0, file_size=123, job_status_id=4)
    jobF = JobFactory(submission_id=1, file_type_id=7, job_type_id=4, number_of_errors=0, file_size=123, job_status_id=4)


    database.session.add_all([submission, jobA, jobB, jobC, jobD1, jobD2, jobE, jobF])
    database.session.commit()

    # Everything ok
    response = file_app.get("/v1/check_current_page/?submission_id=1")
    assert response['step'] == '5'

    jobE.job_status_id = 6
    database.session.commit()
    #E or F failed
    response = file_app.get("/v1/check_current_page/?submission_id=1")
    assert response['step'] == '4'

    jobC.job_status_id = 6
    database.session.commit()
    # Fail C file upload
    response = file_app.get("/v1/check_current_page/?submission_id=1")
    assert response['step'] == '3'

    jobC.number_of_errors = 6
    database.session.commit()
    # Fail C file upload
    response = file_app.get("/v1/check_current_page/?submission_id=1")
    assert response['step'] == '2'

    jobC.number_of_errors = 6
    database.session.commit()
    # Fail C file upload
    response = file_app.get("/v1/check_current_page/?submission_id=1")
    assert response['step'] == '1'
