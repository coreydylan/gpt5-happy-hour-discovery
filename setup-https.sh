#!/bin/bash

echo "🔄 Checking SSL certificate validation status..."

# Check certificate status
CERT_STATUS=$(aws acm describe-certificate --certificate-arn arn:aws:acm:us-east-1:790856971687:certificate/524d1d09-a269-49d8-a67e-8a79acad2245 --region us-east-1 --query 'Certificate.Status' --output text)

if [ "$CERT_STATUS" = "ISSUED" ]; then
    echo "✅ SSL Certificate is validated! Setting up HTTPS..."
    
    # Create HTTPS listener
    echo "🔧 Creating HTTPS listener..."
    aws elbv2 create-listener \
        --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:790856971687:loadbalancer/app/happy-hour-alb/8403fa50a33cbad2 \
        --protocol HTTPS \
        --port 443 \
        --certificates CertificateArn=arn:aws:acm:us-east-1:790856971687:certificate/524d1d09-a269-49d8-a67e-8a79acad2245 \
        --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:790856971687:targetgroup/happy-hour-tg/5b9a69be20046311 \
        --region us-east-1
    
    # Modify HTTP listener to redirect to HTTPS
    echo "🔄 Setting up HTTP to HTTPS redirect..."
    HTTP_LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:790856971687:loadbalancer/app/happy-hour-alb/8403fa50a33cbad2 --region us-east-1 --query 'Listeners[?Port==`80`].ListenerArn' --output text)
    
    aws elbv2 modify-listener \
        --listener-arn $HTTP_LISTENER_ARN \
        --default-actions Type=redirect,RedirectConfig='{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}' \
        --region us-east-1
    
    echo "✅ HTTPS setup complete!"
    echo "🌐 Your secure endpoint: https://hhmap.atlascivica.com"
    
    # Test the HTTPS endpoint
    echo "🧪 Testing HTTPS endpoint..."
    sleep 10
    curl -s https://hhmap.atlascivica.com/health
    
else
    echo "⏳ SSL Certificate status: $CERT_STATUS"
    echo "❌ Certificate not yet validated. Please update nameservers first:"
    echo ""
    echo "🔧 Update your domain registrar for atlascivica.com to use these nameservers:"
    echo "   ns-431.awsdns-53.com"
    echo "   ns-1297.awsdns-34.org" 
    echo "   ns-1709.awsdns-21.co.uk"
    echo "   ns-536.awsdns-03.net"
    echo ""
    echo "Then run this script again to complete HTTPS setup."
fi