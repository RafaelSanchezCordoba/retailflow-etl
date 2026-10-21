import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from retailflow.extract.raw_snapshot import bucket_from_env, client_from_env, upload_file

TEST_DS = "1900-01-01"  # disposable date, never a real ingestion_date

# No teardown delete: retailflow-app's IAM policy grants only List/Put/Get
# (least privilege), not Delete. Re-running this test overwrites the same
# key, same as a real rerun would; the bucket's lifecycle rule expires
# noncurrent versions after 90 days.


@pytest.fixture
def s3():
    try:
        client = client_from_env()
        bucket = bucket_from_env()
        client.head_bucket(Bucket=bucket)
    except (ClientError, NoCredentialsError, KeyError) as exc:
        pytest.skip(f"S3 raw bucket not reachable: {exc}")
    return client, bucket


def test_upload_lands_at_expected_key(s3, tmp_path):
    client, bucket = s3
    path = tmp_path / f"orders_{TEST_DS}.csv"
    path.write_text("order_id,order_line_id\nORD-1,ORD-1-L1\n")

    result = upload_file(path, TEST_DS, client, bucket)

    assert result.key == f"raw/orders/ingestion_date={TEST_DS}/orders_{TEST_DS}.csv"
    head = client.head_object(Bucket=bucket, Key=result.key)
    assert head["ContentLength"] > 0
