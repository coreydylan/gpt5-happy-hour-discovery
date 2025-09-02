# AWS Lambda Deployment - GPT-5 Happy Hour Discovery System

## 🚀 **Quick Start**

Deploy the entire agent fleet to AWS Lambda in 5 minutes:

```bash
# 1. Set environment variables
export SUPABASE_URL="your-supabase-project-url"
export SUPABASE_KEY="your-supabase-service-role-key"  
export OPENAI_API_KEY="your-openai-api-key"

# 2. Deploy to development
cd aws/
./deploy.sh dev

# 3. Deploy to production
./deploy.sh prod
```

## 📋 **Prerequisites**

### **Required Tools**
- [AWS CLI](https://aws.amazon.com/cli/) configured with credentials
- [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
- Python 3.11+
- Docker (for containerized builds)

### **AWS Permissions**
Your AWS user needs permissions for:
- CloudFormation (create/update/delete stacks)
- Lambda (create/update functions)
- IAM (create roles and policies)
- S3 (create buckets, upload objects)
- SQS (create queues)
- CloudWatch (create alarms)

## 🔑 **Environment Variables**

### **Required**
```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsI..."  # Service role key
export OPENAI_API_KEY="sk-..."                   # OpenAI API key
```

### **Optional (Recommended for Full Features)**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."           # Claude API key
export GOOGLE_PLACES_API_KEY="AIza..."          # Google Places API
export YELP_API_KEY="..."                       # Yelp Fusion API
export TWILIO_ACCOUNT_SID="AC..."               # Twilio for voice calls
export TWILIO_AUTH_TOKEN="..."                  # Twilio auth token
```

## 🏗️ **Architecture Overview**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Orchestrator  │───▶│   Task Queue    │───▶│  Agent Fleet    │
│    (FastAPI)    │    │     (SQS)       │    │   (Lambdas)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                              │
         ▼                                              ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Consensus     │◀───│   Evidence      │◀───│   Raw Data      │
│    Engine       │    │   Database      │    │   Storage       │
│   (Lambda)      │    │  (Supabase)     │    │     (S3)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🤖 **Lambda Functions**

### **Core Agent Fleet**
- **Orchestrator**: Job distribution and result aggregation
- **SiteAgent**: Website scraping and PDF processing  
- **GoogleAgent**: Google Business Profile data extraction
- **YelpAgent**: Yelp review analysis and business data
- **VoiceVerifyAgent**: Phone call verification (killer feature!)
- **ConsensusEngine**: Mathematical confidence scoring

### **Resource Allocation**
```yaml
Memory: 1024-2048 MB (depending on function)
Timeout: 60-600 seconds (10 min for voice calls)
Runtime: Python 3.11
Cold Start: ~2-5 seconds with optimization
```

## 📊 **Cost Optimization**

### **Expected Monthly Costs** (1000 restaurant analyses)
```
Lambda Execution:    $15-30
SQS Messages:        $1-2
S3 Storage:          $5-10
CloudWatch Logs:     $5-10
Total AWS:           ~$25-50/month

AI API Costs:        $50-150/month
Twilio Voice:        $10-30/month
Total System:        ~$85-230/month
```

### **Cost Optimization Features**
- **Smart Agent Skipping**: Skip expensive agents when confidence is already high
- **Domain Grouping**: Reuse browser sessions across multiple venues
- **Result Caching**: Avoid re-analyzing recently processed restaurants  
- **Budget Limits**: Hard caps on per-analysis spending

## 🚢 **Deployment Commands**

### **Basic Deployment**
```bash
# Deploy to development environment
./deploy.sh dev

# Deploy to production with all features
./deploy.sh prod
```

### **Advanced Operations**
```bash
# View stack outputs (URLs, ARNs, etc.)
./deploy.sh outputs

# Stream function logs in real-time
./deploy.sh logs OrchestratorFunction

# Delete entire stack (careful!)
./deploy.sh delete dev

# Get help
./deploy.sh help
```

### **Manual SAM Commands**
```bash
# Build only
sam build --use-container

# Deploy with custom parameters
sam deploy --guided

# Local testing
sam local start-api
sam local invoke SiteAgentFunction
```

## 🔧 **Configuration**

### **Environment-Specific Settings**
Edit `template.yaml` parameters:
- **Memory allocation** per function
- **Timeout values** for long-running tasks
- **Concurrency limits** to control costs
- **Environment variables** for different stages

### **Agent Configuration**
Each agent function can be configured via environment variables:
```python
# In agent handler.py
CONFIDENCE_THRESHOLD = float(os.environ.get('CONFIDENCE_THRESHOLD', '0.85'))
MAX_RETRIES = int(os.environ.get('MAX_RETRIES', '3'))
TIMEOUT_SECONDS = int(os.environ.get('TIMEOUT_SECONDS', '30'))
```

## 📈 **Monitoring & Debugging**

### **CloudWatch Dashboards**
- Function execution metrics
- Error rates and duration
- Cost tracking per function
- Queue depth monitoring

### **Log Aggregation**
```bash
# Real-time logs
sam logs -n SiteAgentFunction --tail

# Search logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/happy-hour-site-agent-dev \
  --filter-pattern "ERROR"
```

### **Performance Metrics**
- **Cold Start Time**: Target <3 seconds
- **Execution Duration**: Monitor per-agent performance
- **Success Rate**: Target >95% successful executions
- **Cost Per Analysis**: Track spending efficiency

## 🧪 **Testing**

### **Individual Function Testing**
```bash
# Test site agent with sample restaurant
sam local invoke SiteAgentFunction -e events/sample-restaurant.json

# Test full orchestration flow
curl -X POST https://your-api-gateway-url/analyze \
  -H "Content-Type: application/json" \
  -d '{"name": "Dukes Restaurant", "city": "La Jolla"}'
```

### **Load Testing**
```python
# Use artillery or similar tools
artillery quick --count 10 --num 5 \
  'https://your-api-gateway-url/analyze'
```

## 🚨 **Troubleshooting**

### **Common Issues**

**1. Cold Start Timeouts**
```bash
# Increase timeout in template.yaml
Timeout: 300  # 5 minutes
MemorySize: 2048  # More memory = faster startup
```

**2. Permission Errors**
```bash
# Check IAM role has required permissions
aws iam get-role-policy --role-name HappyHourLambdaRole --policy-name HappyHourAgentPolicy
```

**3. Layer Size Limits**
```bash
# Optimize requirements.txt
pip install --target ./layer/python -r requirements-minimal.txt
```

**4. API Rate Limits**
```bash
# Implement exponential backoff in agent code
time.sleep(min(300, (2 ** attempt) + random.random()))
```

### **Debug Mode**
Set `LOG_LEVEL=DEBUG` environment variable for verbose logging.

## 🔐 **Security Best Practices**

### **API Key Management**
- Store all keys in AWS Parameter Store (not environment variables)
- Use IAM roles for AWS service access
- Rotate keys regularly
- Monitor key usage

### **Network Security**  
- Lambda functions run in AWS VPC
- Supabase uses TLS encryption
- API Gateway with rate limiting
- CloudTrail logging enabled

## 📚 **Next Steps**

1. **Monitor Performance**: Set up CloudWatch dashboards
2. **Optimize Costs**: Tune memory/timeout settings based on actual usage
3. **Scale Testing**: Test with higher restaurant volumes
4. **Add Features**: Deploy additional agent types as needed
5. **Production Hardening**: Enable advanced monitoring and alerting

## 🆘 **Support**

For deployment issues:
1. Check CloudFormation stack events in AWS Console
2. Review function logs in CloudWatch
3. Verify environment variables are set correctly
4. Ensure AWS permissions are configured properly

---

**Built for speed, optimized for cost, designed to scale** 🚀