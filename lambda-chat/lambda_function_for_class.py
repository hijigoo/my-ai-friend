import io
import json
import boto3
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage

# S3 클라이언트 생성
s3 = boto3.client('s3')

# 모델 Id 선언
model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

# Bucket 이름 선언
bucket_name = "my-ai-friend-bucket-0122"


def get_info(file_key):
    json_data = {}

    try:
        # S3 파일 경로 설정
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


def get_history(file_key):
    text_data = ""

    try:
        # S3 버킷 이름과 파일 경로 설정
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


def create_prompt(info, history, query):
    ai_info = f"이름: {info.get('ai-name', '')}, 성격: {info.get('ai-character', '')}, 생긴모습: {info.get('ai-prompt', '')}"
    user_info = f"이름: {info.get('my-name', '')}, 나이: {info.get('my-age', '')}, 취미: {info.get('my-hobby', '')}, 좋아하는 것: {info.get('my-like', '')}, AI에게 하고 싶은 말: {info.get('my-etc', '')}"

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
    return prompt


def invoke_llm(prompt):
    llm = ChatBedrock(
        model_id=model_id,
        streaming=False,
        model_kwargs={
            "max_tokens": 512,
            "temperature": 1,
            "top_k": 250,
            "top_p": 1,
            "stop_sequences": ["\n\nHuman"],
        }
    )

    messages = [
        HumanMessage(
            content=prompt
        )
    ]

    result = llm.invoke(messages)

    return result.content


def update_history(file_key, answer, history, query):
    # Make history
    prev_query = query
    prev_answer = answer
    next_history = f"""Human: {prev_query}
AI: {prev_answer}
"""
    # Save history
    next_history = history + next_history
    s3.put_object(Body=next_history, Bucket=bucket_name, Key=file_key)
    print(f"JSON 파일이 {file_key} 경로에 성공적으로 업데이트되었습니다.")


def lambda_handler(event, context):
    id = event["queryStringParameters"]['id']
    query = event["queryStringParameters"]['query']

    if query.strip() == 'DELETE HISTORY':
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
    info = get_info(f'info/{id}_info.json')

    # Read history file
    history = get_history(f'info/{id}_history.txt')

    # Create Prompt
    prompt = create_prompt(info, history, query)

    # Get answer
    answer = invoke_llm(prompt)

    # Update History
    update_history(f'info/{id}_history.txt', answer, history, query)

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
