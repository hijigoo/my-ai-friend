import * as cdk from 'aws-cdk-lib';
import {Construct} from 'constructs';

import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apiGateway from 'aws-cdk-lib/aws-apigateway';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3Deployment from 'aws-cdk-lib/aws-s3-deployment';
import * as iam from 'aws-cdk-lib/aws-iam';


const stage = 'default';
const projectName = 'my-ai-friend';

const modelId = "anthropic.claude-3-sonnet-20240229-v1:0"
const imageModelId = "stability.stable-diffusion-xl-v1"

const pythonRuntimeVersion = lambda.Runtime.PYTHON_3_11
const architecture = lambda.Architecture.X86_64

export class CdkMyAiFriendStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);


    // 1. App 에서 사용할 S3 버킷 생성
    const bucketName = `${projectName}-bucket-0410`
    const existingBucket = s3.Bucket.fromBucketName(this, `${projectName}-check-bucket`, bucketName);
    const assetsBucket = existingBucket || new s3.Bucket(this, `${projectName}-bucket`, {
      bucketName: `${projectName}-bucket-0410`, // 버킷 이름 지정
      removalPolicy: cdk.RemovalPolicy.DESTROY, // 스택 삭제 시 버킷도 삭제
    });

    // 1-1. Execute Role 생성
    const executeRole = new iam.Role(this, `${projectName}-api-execution-role`, {
      assumedBy: new iam.ServicePrincipal('apigateway.amazonaws.com'),
      roleName: `${projectName}-API-Gateway-role`,
    });
    executeRole.addToPolicy(
      new iam.PolicyStatement({
        resources: [assetsBucket.bucketArn],
        actions: ["s3:Get"],
      })
    );

    // 1-2. Bucket 에 Execute Role 추가
    assetsBucket.grantReadWrite(executeRole);


    // 2. HTML, Data 파일업로드
    new s3Deployment.BucketDeployment(this, `${projectName}-deploy-html-files`, {
      sources: [s3Deployment.Source.asset('./../html')],
      destinationBucket: assetsBucket,
      destinationKeyPrefix: "html/"
    });
    new s3Deployment.BucketDeployment(this, `${projectName}-deploy-data-files`, {
      sources: [s3Deployment.Source.asset('./../data')],
      destinationBucket: assetsBucket,
      destinationKeyPrefix: "data/"
    });


    // 3. Lambda 함수 생성
    // 3-1. Lambda 함수에서 공통으로 사용할 Role 생성
    const lambdaRole = new iam.Role(this, `${projectName}-lambda-role`, {
      roleName: `${projectName}-lambda-role`,
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
    });

    lambdaRole.addToPolicy(
      new iam.PolicyStatement({  // policy statement for bedrock
        effect: iam.Effect.ALLOW,
        actions: ['s3:GetObject', 's3:PutObject'],
        resources: [`${assetsBucket.bucketArn}/*`],
      })
    )
    lambdaRole.addToPolicy(
      new iam.PolicyStatement({  // policy statement for bedrock
        effect: iam.Effect.ALLOW,
        actions: ['bedrock:*'],
        resources: [`*`],
      })
    );

    // 3-2. Lambda 함수에서 필요한 라이브러리를 포함하는 Lambda Layer 생성
    const packageLayer = new lambda.LayerVersion(this, `${projectName}-package-layer`, {
      code: lambda.Code.fromAsset('../package-layer/package-layer.zip'),
      layerVersionName: `${projectName}-package-layer`,
      compatibleRuntimes: [pythonRuntimeVersion],
      compatibleArchitectures: [architecture],
      description: 'Lambda package layer for Lambda functions',
    });

    // 3-3. 채팅을 위한 Lambda Function 생성
    const lambdaChat = new lambda.Function(this, `${projectName}-chat`, {
      functionName: `${projectName}-chat`,
      runtime: pythonRuntimeVersion,
      architecture: architecture,
      handler: "lambda_function.lambda_handler",
      role: lambdaRole,
      code: lambda.Code.fromAsset('../lambda-chat'),
      timeout: cdk.Duration.minutes(15),
      description: "lambda function to chat",
      layers: [packageLayer],
      environment: {
        assetsBucketName: assetsBucket.bucketName,
        modelId: modelId,
      }
    });

    // 3-4. 이미지 생성하는 Lambda Function 생성
    const lambdaImageGenerator = new lambda.Function(this, `${projectName}-image-generate`, {
      functionName: `${projectName}-image-generate`,
      runtime: pythonRuntimeVersion,
      architecture: architecture,
      handler: "lambda_function.lambda_handler",
      role: lambdaRole,
      code: lambda.Code.fromAsset('../lambda-image-generate'),
      timeout: cdk.Duration.minutes(15),
      description: "lambda function to generate image",
      layers: [packageLayer],
      environment: {
        assetsBucketName: assetsBucket.bucketName,
        imageModelId: imageModelId
      }
    });

    // 3-5. 사용자 정보 업데이트 하는 Lambda Function 생성
    const lambdaInfoUpdate = new lambda.Function(this, `${projectName}-info-update`, {
      functionName: `${projectName}-info-update`,
      runtime: pythonRuntimeVersion,
      architecture: architecture,
      handler: "lambda_function.lambda_handler",
      role: lambdaRole,
      code: lambda.Code.fromAsset('../lambda-info-update'),
      timeout: cdk.Duration.minutes(15),
      description: "lambda function to update user info",
      layers: [packageLayer],
      environment: {
        assetsBucketName: assetsBucket.bucketName,
      }
    });

    // 3-6. 사용자 정보를 요약 하는 Lambda Function 생성
    const lambdaSummary = new lambda.Function(this, `${projectName}-summary`, {
      functionName: `${projectName}-summary`,
      runtime: pythonRuntimeVersion,
      architecture: architecture,
      handler: "lambda_function.lambda_handler",
      role: lambdaRole,
      code: lambda.Code.fromAsset('../lambda-summary'),
      timeout: cdk.Duration.minutes(15),
      description: "lambda function to summary user info",
      layers: [packageLayer],
      environment: {
        assetsBucketName: assetsBucket.bucketName,
        modelId: modelId
      }
    });

    // 4. API Gateway 생성
    const restApi = new apiGateway.RestApi(this, `${projectName}-api-gateway`, {
      restApiName: `${projectName}-api-gateway`,
      description: `API Gateway for ${projectName}`,
      endpointTypes: [apiGateway.EndpointType.REGIONAL],
      binaryMediaTypes: ['*/*'],
      deployOptions: {
        stageName: stage,
      }
    });


    // 4-1. API Gateway 의 API 생성
    const api = restApi.root.addResource('api')

    // 4-2 채팅을 위한 API 설정
    const apiLambdaChat = api.addResource('lambda-chat')

    // 4-2-1. Chat Lambda 연결을 위한 integration 설정
    const chatLambdaIntegration = new apiGateway.LambdaIntegration(lambdaChat, {
      proxy: true,
      passthroughBehavior: apiGateway.PassthroughBehavior.WHEN_NO_TEMPLATES,
      integrationResponses: [{
        statusCode: '200',
      }],
    })

    // 4-2-2. Chat Lambda 와 API 연결
    apiLambdaChat.addMethod('GET', chatLambdaIntegration, {
      requestParameters: {
        "method.request.querystring.id": true,
        "method.request.querystring.query": true,
      },
      methodResponses: [
        {
          statusCode: "200",
          responseModels: {
            "application/json": apiGateway.Model.EMPTY_MODEL
          }
        },
      ],
    });

    // 4-3. 이미지 생성을 위한 API 설정
    const apiLambdaImageGenerator = api.addResource('lambda-image-generate')

    // 4-3-1. Image Generator Lambda 연결을 위한 integration 설정
    const imageGeneratorLambdaIntegration = new apiGateway.LambdaIntegration(lambdaImageGenerator, {
      proxy: true,
      passthroughBehavior: apiGateway.PassthroughBehavior.WHEN_NO_TEMPLATES,
      integrationResponses: [{
        statusCode: '200',
      }],
    })

    // 4-3-2. Image Generator Lambda 와 API 연결
    apiLambdaImageGenerator.addMethod('GET', imageGeneratorLambdaIntegration, {
      requestParameters: {
        "method.request.querystring.id": true,
        "method.request.querystring.prompt": true,
      },
      methodResponses: [
        {
          statusCode: "200",
          responseModels: {
            "application/json": apiGateway.Model.EMPTY_MODEL
          }
        },
      ],
    });

    // 4-4. 사용자 정보 업데이트를 위한 API 설정
    const apiLambdaInfoUpdate = api.addResource('lambda-info-update')

    // 4-4-1. Info Update Lambda 연결을 위한 integration 설정
    const infoUpdateLambdaIntegration = new apiGateway.LambdaIntegration(lambdaInfoUpdate, {
      proxy: true,
      passthroughBehavior: apiGateway.PassthroughBehavior.WHEN_NO_TEMPLATES,
      integrationResponses: [{
        statusCode: '200',
      }],
    })

    // 4-4-2. Info Update Lambda 와 API 연결
    apiLambdaInfoUpdate.addMethod('GET', infoUpdateLambdaIntegration, {
      requestParameters: {
        "method.request.querystring.ai-character": false,
        "method.request.querystring.ai-name": false,
        "method.request.querystring.id": true,
        "method.request.querystring.my-age": false,
        "method.request.querystring.my-etc": false,
        "method.request.querystring.my-hobby": false,
        "method.request.querystring.my-like": false,
        "method.request.querystring.my-name": false,
      },
      methodResponses: [
        {
          statusCode: "200",
          responseModels: {
            "application/json": apiGateway.Model.EMPTY_MODEL
          }
        },
      ],
    });

    // 4-5. 사용자 정보 요약 위한 API 설정
    const apiLambdaSummary = api.addResource('lambda-summary')

    // 4-5-1. Summary Lambda 연결을 위한 integration 설정
    const summaryLambdaIntegration = new apiGateway.LambdaIntegration(lambdaSummary, {
      proxy: true,
      passthroughBehavior: apiGateway.PassthroughBehavior.WHEN_NO_TEMPLATES,
      integrationResponses: [{
        statusCode: '200',
      }],
    })

    // 4-5-2. Summary Lambda 와 API 연결
    apiLambdaSummary.addMethod('GET', summaryLambdaIntegration, {
      requestParameters: {
        "method.request.querystring.id": true,
      },
      methodResponses: [
        {
          statusCode: "200",
          responseModels: {
            "application/json": apiGateway.Model.EMPTY_MODEL
          }
        },
      ],
    });

    // 4-6. S3에서 이미지를 가져오기 위한 API 설정
    const apiData = restApi.root.addResource('data')
    const apiDataObject = apiData.addResource('{object}')

    // 4-6-1. S3 integration 설정
    const dataS3Integration = new apiGateway.AwsIntegration({
      service: 's3',
      integrationHttpMethod: 'GET',
      path: `${assetsBucket.bucketName}/data/{object}`,
      options: {
        credentialsRole: executeRole,
        integrationResponses: [
          {
            statusCode: "200",
            responseParameters: {
              "method.response.header.Content-Type": "integration.response.header.Content-Type",
            },
          },
        ],
        requestParameters: {
          "integration.request.path.object": "method.request.path.object",
        },
      },
    });

    // 4-6-2. S3 integration 연결
    apiDataObject.addMethod('GET', dataS3Integration, {
      requestParameters: {
        "method.request.path.object": true,
        "method.request.header.Content-Type": true,
      },
      methodResponses: [
        {
          statusCode: "200",
          responseParameters: {
            "method.response.header.Content-Type": true,
          },
        },
      ],
    });


    // 4-7. S3에서 HTML 을 가져오기 위한 API 설정
    const apiHtml = restApi.root.addResource('html')
    const apiHtmlObject = apiHtml.addResource('{object}')

    // 4-7-1. S3 integration 설정
    const htmlS3Integration = new apiGateway.AwsIntegration({
      service: 's3',
      integrationHttpMethod: 'GET',
      path: `${assetsBucket.bucketName}/html/{object}`,
      options: {
        credentialsRole: executeRole,
        integrationResponses: [
          {
            statusCode: "200",
            responseParameters: {
              "method.response.header.Content-Type": "integration.response.header.Content-Type",
            },
          },
        ],
        requestParameters: {
          "integration.request.path.object": "method.request.path.object",
        },
      },
    });

    // 4-7-2. S3 integration 연결
    apiHtmlObject.addMethod('GET', htmlS3Integration, {
      requestParameters: {
        "method.request.path.object": true,
        "method.request.header.Content-Type": true,
      },
      methodResponses: [
        {
          statusCode: "200",
          responseParameters: {
            "method.response.header.Content-Type": true,
          },
        },
      ],
    });

    new cdk.CfnOutput(this, 'Webpage URL', {
      value: restApi.url + "html/index.html",
      description: 'Webpage URL',
    });

    // 4-8. S3에서 사용자 정보를가져오기 위한 API 설정
    const apiInfo = restApi.root.addResource('info')
    const apiInfoObject = apiInfo.addResource('{object}')

    // 4-8-1. S3 integration 설정
    const infoS3Integration = new apiGateway.AwsIntegration({
      service: 's3',
      integrationHttpMethod: 'GET',
      path: `${assetsBucket.bucketName}/info/{object}`,
      options: {
        credentialsRole: executeRole,
        integrationResponses: [
          {
            statusCode: "200",
            responseParameters: {
              "method.response.header.Content-Type": "integration.response.header.Content-Type",
            },
          },
        ],
        requestParameters: {
          "integration.request.path.object": "method.request.path.object",
        },
      },
    });

    // 4-8-2. S3 integration 연결
    apiInfoObject.addMethod('GET', infoS3Integration, {
      requestParameters: {
        "method.request.path.object": true,
        "method.request.header.Content-Type": true,
      },
      methodResponses: [
        {
          statusCode: "200",
          responseParameters: {
            "method.response.header.Content-Type": true,
          },
        },
      ],
    });

  }
}
