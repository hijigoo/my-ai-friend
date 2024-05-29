import json
import json
import boto3
from botocore.exceptions import ClientError

# S3 클라이언트 생성
s3 = boto3.client('s3')


def update_if_exist(event, key, data):
    if 'queryStringParameters' in event:
        query_params = event['queryStringParameters']

        # id 키가 있는지 확인
        if key in query_params:
            value = query_params[key]
            # 내용이 있는지 확인
            if value.strip() != "":
                print(f"{key} 에 대한 값: {value}")
                data[key] = value.strip()
        else:
            print(f"{key} 가 없습니다.")
    else:
        print("queryStringParameters가 없습니다.")
    return data


def lambda_handler(event, context):
    # id 가져오기
    id = event["queryStringParameters"]['id']

    # S3 버킷 이름과 파일 경로 설정
    bucket_name = 'coding-school-2024'
    file_key = f'info/{id}_info.json'

    json_data = {}
    try:
        # head_object 메서드를 사용하여 파일 존재 여부 확인
        s3.head_object(Bucket=bucket_name, Key=file_key)
        print(f"{file_key} 파일이 {bucket_name} 버킷에 존재합니다.")

        # S3에서 JSON 파일 읽기
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        json_data = json.loads(response['Body'].read())

    except s3.exceptions.ClientError as e:
        # 404 에러가 발생하면 파일이 없는 것
        if e.response['Error']['Code'] == '404':
            print(f"{file_key} 파일이 {bucket_name} 버킷에 없습니다.")
        else:
            # 다른 에러가 발생한 경우 예외 처리
            print(f"에러 발생: {e}")

    updated_json_data = {}
    try:

        # JSON 데이터에 새로운 항목 추가
        update_if_exist(event, 'ai-name', json_data)
        update_if_exist(event, 'ai-character', json_data)
        update_if_exist(event, 'my-name', json_data)
        update_if_exist(event, 'my-age', json_data)
        update_if_exist(event, 'my-hobby', json_data)
        update_if_exist(event, 'my-like', json_data)
        update_if_exist(event, 'my-etc', json_data)

        # 업데이트된 JSON 데이터를 문자열로 변환
        updated_json_data = json.dumps(json_data, ensure_ascii=False)

        # S3에 업데이트된 JSON 파일 업로드
        s3.put_object(Body=updated_json_data, Bucket=bucket_name, Key=file_key)
        print(f"JSON 파일이 {file_key} 경로에 성공적으로 업데이트되었습니다.")

    except ClientError as e:
        print(f"S3 작업 중 에러가 발생했습니다: {e.response['Error']['Message']}")
    except Exception as e:
        print(f"예기치 않은 에러가 발생했습니다: {str(e)}")

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json; charset=UTF-8',
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,X-Amz-Security-Token,Authorization,X-Api-Key,X-Requested-With,Accept,Access-Control-Allow-Methods,Access-Control-Allow-Origin,Access-Control-Allow-Headers",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "X-Requested-With": "*"
        },
        'body': updated_json_data
    }
