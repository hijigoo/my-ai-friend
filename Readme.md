# AWS CDK 설정
[Getting started with the AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html)

npm -g install typescript
npm install -g aws-cdk
cdk --version

cdk bootstrap aws://123456789012/us-east-1


# Lambda Layer 설정
[Working with layers for Python Lambda functions](https://docs.aws.amazon.com/lambda/latest/dg/python-layers.html)

## Lambda Layer 패키지 만들기
cd package-layer

### (Option) 기존 파일이 있는 경우 삭제
rm -rf layer_venv
rm -rf python
rm package-layer.zip

### 새로 만들기
python3.11 -m venv layer_venv
source layer_venv/bin/activate
pip install -r requirements.txt
pip install --platform manylinux2014_x86_64 --target=layer_venv/lib/python3.11/site-packages --no-deps --upgrade -r requirements.txt
mkdir python
cp -r layer_venv/lib python/
zip -r package-layer.zip python

cd ../cdk-my-ai-friend
cdk deploy