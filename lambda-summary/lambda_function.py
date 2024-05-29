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


def get_llm(max_tokens=512, temperature=0.8, top_k=125, top_p=1):
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
    print(f"Selected region is {selected_region}")

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


def get_info(id):
    json_data = {}
    # Read and Update info file#####
    file_key = f'info/{id}_info.json'
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
    # file_path = f"tmp/titan/ai_info_{id}.txt"
    # info = read_ai_info(file_path=file_path)

    id = event["queryStringParameters"]['id']

    # Read and Update info file#####
    info = get_info(id)

    ai_info = f"이름: {info.get('ai-name', '')}, 성격: {info.get('ai-character', '')}, 생긴모습: {info.get('ai-prompt', '')}"
    user_info = f"이름: {info.get('my-name', '')}, 나이: {info.get('my-age', '')}, 취미: {info.get('my-hobby', '')}, 좋아하는 것: {info.get('my-like', '')}, AI에게 하고 싶은 말: {info.get('my-etc', '')}"

    prompt = f"""
ai 가 사용자에게 자신을 소개하는 문장을 모두 한글로 만들거야.
사용자는 어린이고 이름이 있다면 제일 먼저 불러줘. 그리고 만들어줘서 고맙다고 애기해.
너는 매우 친절한 ai 임을 명심해. 최종 출력은 모두 한글로 번역하고 태그와 영어는 포함하지 말아줘.
친구에게 말 하듯이 일관된 말투를 사용해. 존댓말은 하지마.

<ai-info>
{ai_info}
</ai-info> 

<user>
{user_info}
</user>

활용해야 할 ai 정보는 <ai-info> 태그 안에 있고 사용자 정보는 <user> 태그 안에 있어
없는 정보는 활용하지 말고 있는 정보는 최대한 활용해.
짧게 요약해.

"""

    # Get answer
    answer = invoke_llm(prompt)

    result = {
        "answer": answer
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


