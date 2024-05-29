import json
import os
import io
import base64
import boto3
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage
import random

boto3_bedrock = boto3.client('bedrock-runtime')

# S3 클라이언트 생성
s3 = boto3.client('s3')

model_id = "anthropic.claude-3-sonnet-20240229-v1:0"


# model_id = "anthropic.claude-3-haiku-20240307-v1:0"


def get_llm(max_tokens=512, temperature=1, top_k=250, top_p=1):
    model_kwargs = {
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_k": top_k,
        "top_p": top_p,
        "stop_sequences": ["\n\nHuman"],
    }

    # Sonnet
    region_name = ["us-west-2", "us-east-1", "ap-southeast-2", "eu-west-3"]
    selected_region = random.choice(region_name)
    print(f"Selected region: {selected_region}")

    return ChatBedrock(
        region_name=selected_region,
        model_id=model_id,
        streaming=False,
        # callbacks=[StreamingStdOutCallbackHandler()],
        model_kwargs=model_kwargs
    )


def invoke_llm(prompt):
    messages = [
        HumanMessage(
            content=prompt
        )
    ]
    llm = get_llm()
    result = llm.invoke(messages)

    return result.content


def read_history(file_path):
    history = ""
    # Read history
    if os.path.isfile(file_path):
        # 파일 열기 (읽기 모드)
        file = open(file_path, "r", encoding="utf-8")

        # 파일 전체 내용 읽기
        lines = file.readlines()

        # 마지막 5줄 출력
        num_lines = min(30, len(lines))
        for line in lines[-num_lines:]:
            history = history + line.strip() + "\n"
        print(history)
        # 파일 닫기
        file.close()
    return history


def get_text(id, file_key):
    text_data = ""

    try:
        # S3 버킷 이름과 파일 경로 설정
        bucket_name = 'coding-school-2024'
        s3.head_object(Bucket=bucket_name, Key=file_key)
        print(f"{file_key} 파일이 {bucket_name} 버킷에 존재합니다.")

        # S3에서 JSON 파일 읽기
        response_body = s3.get_object(Bucket=bucket_name, Key=file_key)
        file_content = response_body['Body'].read().decode('utf-8')

        # 파일 내용 출력
        print(file_content)

        stream = io.StringIO(file_content)
        lines = stream.readlines()

        # 마지막 5줄 출력
        num_lines = min(10, len(lines))
        for line in lines[-num_lines:]:
            text_data = text_data + line.strip() + "\n"

    except s3.exceptions.ClientError as e:
        # 404 에러가 발생하면 파일이 없는 것
        if e.response['Error']['Code'] == '404':
            print(f"{file_key} 파일이 {bucket_name} 버킷에 없습니다.")
        else:
            # 다른 에러가 발생한 경우 예외 처리
            print(f"에러 발생: {e}")
    return text_data


def get_json(id, file_key):
    json_data = {}

    try:
        # S3 버킷 이름과 파일 경로 설정
        bucket_name = 'coding-school-2024'
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
    return json_data


def lambda_handler(event, context):
    id = event["queryStringParameters"]['id']
    query = event["queryStringParameters"]['query']

    if query.strip() == 'DELETE HISTORY':
        bucket_name = 'coding-school-2024'
        file_key = f'info/{id}_history.txt'
        s3.put_object(Body="", Bucket=bucket_name, Key=file_key)
        return {
            'statusCode': 200,
            'headers': {
                "Content-Type": "application/json; charset=UTF-8",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,X-Amz-Security-Token,Authorization,X-Api-Key,X-Requested-With,Accept,Access-Control-Allow-Methods,Access-Control-Allow-Origin,Access-Control-Allow-Headers",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "X-Requested-With": "*"
            },
            'body': 'DELETE'
        }

    # Read info file
    info = get_json(id, f'info/{id}_info.json')

    ai_info = f"이름: {info.get('ai-name', '')}, 성격: {info.get('ai-character', '')}, 생긴모습: {info.get('ai-prompt', '')}"
    user_info = f"이름: {info.get('my-name', '')}, 나이: {info.get('my-age', '')}, 취미: {info.get('my-hobby', '')}, 좋아하는 것: {info.get('my-like', '')}, AI에게 하고 싶은 말: {info.get('my-etc', '')}"

    # Read history file
    history = get_text(id, f'info/{id}_history.txt')

    prompt = f"""
너는 어린이의 매우 친절한 인공지능 친구야.
너의 정보는 <ai> tag 안에 있어. 너를 만들었으며 지금 대화중인 사람의 정보는 <user> tag 안에 있어.
답변할 때는 인공지능의 정보와 대화중인 사람의 정보를 참고해줘. 항상 언급하진 안아도 돼.

<ai>
{ai_info}
</ai> 

<user>
{user_info}
</user>

Current conversation:
<history>
{history}
</history>

<query>
{query}
</query>

<history> tag 안에 있는 대화 기록 다음으로 주어진 <query> tag 안에 있는 질문에 대해서 대답해 줘.
생성하는 응답중에 영어는 모두 한글로 번역하고해줘. 대답할 때 태그는 모두 제외해줘.
대답은 모두 한 줄로 많이 짧게 해줘.
"""

    # Get answer
    answer = invoke_llm(prompt)

    # Make history
    prev_query = query
    prev_answer = answer
    next_history = f"""Human: {prev_query}
AI: {prev_answer}
"""
    # Save history
    next_history = history + next_history
    bucket_name = 'coding-school-2024'
    file_key = f'info/{id}_history.txt'
    s3.put_object(Body=next_history, Bucket=bucket_name, Key=file_key)
    print(f"JSON 파일이 {file_key} 경로에 성공적으로 업데이트되었습니다.")

    result = {
        "answer": answer,
        "query": query,
    }

    return {
        'statusCode': 200,
        'headers': {
            "Content-Type": "application/json; charset=UTF-8",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,X-Amz-Security-Token,Authorization,X-Api-Key,X-Requested-With,Accept,Access-Control-Allow-Methods,Access-Control-Allow-Origin,Access-Control-Allow-Headers",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "X-Requested-With": "*"
        },
        'body': json.dumps(result, ensure_ascii=False)
    }

