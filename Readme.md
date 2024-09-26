# 나만의 AI 친구 만들기

사용자가 자신만의 AI 캐릭터를 만들어 다양한 주제로 대화할 수 있는 애플리케이션입니다. 

----
## 1. Application

사용자는 AI의 외형, 성격, 특징 등을 자유롭게 설정할 수 있으며, AI는 사용자의 관심사와 선호도를 반영하여 개인화된 대화를 제공합니다. 또한 다양한 AI 캐릭터를 생성하고 설정을 변경할 수 있어 창의적인 상호작용이 가능합니다.

![product-screenshot](https://github.com/user-attachments/assets/78610593-f1df-48ae-83f1-a27fc67969b1)
![product-screenshot](https://github.com/user-attachments/assets/49a84352-63bc-4f8e-85de-d8044348d63d)

## 2. Architecture

### 2.1. 정적 웹호스팅 & 데이터 관리
사용자는 Amazon API Gateway를 통해 Amazon S3에서 호스팅되는 웹사이트에 접근할 수 있습니다.

![architecture](https://github.com/user-attachments/assets/500f6602-9c8a-4558-ac40-1b72e790e8d4)

- Amazon API Gateway: 사용자의 요청을 받아서 S3 에 있는 정적 웹 파일들을 전달합니다.
- Amazon S3 정적 웹 호스팅: HTML, CSS, JavaScript 파일과 같은 정적 콘텐츠를 사용자에게 빠르고 안정적으로 전달합니다.

### 2.2. 서버리스 아키텍처
서버리스 아키텍처를 사용하여 확장성과 유연성을 높혔습니다.

![architecture](https://github.com/user-attachments/assets/c332b7d0-d2d3-4b87-8873-ddc28a9acff8)

주요 구성 요소는 다음과 같습니다:

- Amazon API Gateway: 사용자의 요청을 받아 AWS Lambda 함수로 라우팅합니다.
- AWS Lambda: 애플리케이션 구동에 필요한 API 비지니스 로직을 실행합니다. 
- Amazon S3: 사용자 정보, AI 정보, 채팅 히스토리 등의 데이터를 저장합니다.

애플리케이션의 로직은 크게 4가지 Lambda 함수로 구성됩니다:

- Chat 함수: 사용자의 채팅 요청을 처리하여 실시간 응답을 제공합니다. S3에서 사용자 정보와 AI 정보, 채팅 히스토리를 읽어와 실시간 대화를 가능하게 합니다.
- Image Generate 함수: 사용자의 이미지 생성 요청을 처리하여 이미지를 생성하고 결과를 반환합니다.
- Summary 함수: 사용자 정보를 기반으로 파운데이션 모델이 사용자에 대한 요약 정보를 제공합니다.
- Update Info 함수: 사용자가 정보를 업데이트하면 이를 처리하여 최신 정보를 S3에 저장합니다.

### 2.3. 생성형 AI
Amazon Bedrock와 AI 모델을 활용하여 다양한 기능을 제공합니다.

![architecture](https://github.com/user-attachments/assets/6d1fee20-1f95-40f9-8c8b-f1213c5d1b68)

- AI 이미지 생성: Stability AI의 Stable Diffusion XL 모델을 사용하여 사용자 입력 텍스트에 맞는 이미지를 생성합니다.
- 자연어 처리: Claude 3.5 Sonnet 모델 기반으로 채팅, 요약 등의 기능을 제공하여 사용자와 자연스러운 대화가 가능합니다.


## 3. Lambda 함수 호출 흐름

## 3.1. Update Info

사용자와 AI 의 정보를 업데이트합니다.

![sequence-diagram](https://github.com/user-attachments/assets/e7df12dc-258e-4cae-a5a8-f418ce67073f)

## 3.2. Generate Image

AI 의 이미지를 생성합니다.

![sequence-diagram](https://github.com/user-attachments/assets/56bd2326-cf51-498b-bc5d-384c97530b91)

## 3.3. Summary
사용자와 AI 정보 요약하기. 요약정보는 AI의 첫 대화 인사말로 사용됩니다.

![sequence-diagram](https://github.com/user-attachments/assets/3c275694-a291-44b9-9b29-c839480bd0da)

## 3.4. Chat

AI 와 대화를 합니다.

![sequence-diagram](https://github.com/user-attachments/assets/3f58053a-23d3-482c-8874-980728e30eb1)


## 4. 시작하기

### 4.1. Amazon Bedrock Model 활성화하기
Amazon Bedrock 콘솔로 이동하세요. 화면 왼쪽에서 아래로 스크롤하여 Model access를 선택합니다. 오른쪽에서 주황색 Manage model access 버튼을 선택후 사용 하려는 모델을 모두 Enabled 로 변경합니다.

- Claude 3 Sonnet
- Claude 3.5 Sonnet (선택)
    - Claude 3.5 Sonnet 모델 사용시 [cdk-my-ai-friend-stack.ts](https://github.com/hijigoo/my-ai-friend/blob/main/cdk-my-ai-friend/lib/cdk-my-ai-friend-stack.ts) 에서 modelId 를 변경해주시면 됩니다.
- Stable Diffusion XL

![image](https://github.com/user-attachments/assets/4e5b6294-1771-495f-a174-64125b9cd8aa)


### 4.2. AWS CDK 설정
[Getting started with the AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html)

```
npm -g install typescript
npm install -g aws-cdk
cdk --version
cdk bootstrap aws://123456789012/us-east-1
```

### 4.3. CDK로 배포 하기
```
cd cdk-my-ai-friend
npm i aws-cdk-lib
cdk deploy
```

## 5. (Optional) Lambda Layer 설정
애플리케이션 코드에 포함되어 있기 때문에 필수로 수행해야 하는 단계는 아닙니다.
참고: [Working with layers for Python Lambda functions](https://docs.aws.amazon.com/lambda/latest/dg/python-layers.html)

### 5.1. 패키지 만들기
```
cd package-layer
```

### 5.2. 기존 파일이 있는 경우 삭제
```
rm -rf layer_venv
rm -rf python
rm package-layer.zip
```

### 5.3. 새로 만들기
```
python3.11 -m venv layer_venv
source layer_venv/bin/activate
pip install -r requirements.txt
pip install --platform manylinux2014_x86_64 --target=layer_venv/lib/python3.11/site-packages --no-deps --upgrade -r requirements.txt
mkdir python
cp -r layer_venv/lib python/
zip -r package-layer.zip python
```

## 6. Contribution

**김기철 (Kichul Kim)**
- E-mail: kichul@amazon.com (hi.jigoo@gmail.com)
- LinkedIn: https://www.linkedin.com/in/kichul-kim-4bb293135/

**최지선 (Jisun Choi)**
- E-mail: jschoii@amazon.com (jisunn0130@gmail.com)
- LinkedIn: https://www.linkedin.com/in/지선-최-5a8666a6/
