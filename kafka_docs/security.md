# Kafka Security

## Tổng quan

Kafka hỗ trợ nhiều tính năng bảo mật:

1. **Authentication**: Xác thực clients và brokers
2. **Authorization**: Kiểm soát quyền truy cập
3. **Encryption**: Mã hóa dữ liệu truyền tải
4. **Audit**: Logging các hoạt động

## Authentication

### SSL/TLS Authentication

#### 1. Generate Certificates

**Create CA (Certificate Authority):**
```bash
# Generate CA key
openssl req -new -x509 -keyout ca-key -out ca-cert -days 365

# Import CA vào truststore
keytool -keystore kafka.server.truststore.jks -alias CARoot \
  -import -file ca-cert
```

**Create Broker Certificates:**
```bash
# Generate keystore
keytool -keystore kafka.server.keystore.jks -alias localhost \
  -validity 365 -genkey -keyalg RSA

# Export certificate
keytool -keystore kafka.server.keystore.jks -alias localhost \
  -certreq -file cert-file

# Sign certificate
openssl x509 -req -CA ca-cert -CAkey ca-key \
  -in cert-file -out cert-signed -days 365 -CAcreateserial

# Import CA vào keystore
keytool -keystore kafka.server.keystore.jks -alias CARoot \
  -import -file ca-cert

# Import signed certificate
keytool -keystore kafka.server.keystore.jks -alias localhost \
  -import -file cert-signed
```

#### 2. Broker Configuration

```properties
# SSL Configuration
listeners=SSL://broker1:9093
advertised.listeners=SSL://broker1:9093

# SSL settings
ssl.keystore.location=/var/private/ssl/kafka.server.keystore.jks
ssl.keystore.password=password
ssl.key.password=password
ssl.truststore.location=/var/private/ssl/kafka.server.truststore.jks
ssl.truststore.password=password

# Client authentication
ssl.client.auth=required

# Enabled protocols
ssl.enabled.protocols=TLSv1.2,TLSv1.3

# Cipher suites
ssl.cipher.suites=TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384

# Security protocol
security.inter.broker.protocol=SSL
```

#### 3. Client Configuration

**Producer/Consumer:**
```properties
bootstrap.servers=broker1:9093
security.protocol=SSL

ssl.truststore.location=/var/private/ssl/kafka.client.truststore.jks
ssl.truststore.password=password

# If client authentication required
ssl.keystore.location=/var/private/ssl/kafka.client.keystore.jks
ssl.keystore.password=password
ssl.key.password=password
```

### SASL Authentication

#### SASL/PLAIN

**Broker Configuration:**
```properties
# Listeners
listeners=SASL_PLAINTEXT://broker1:9092
advertised.listeners=SASL_PLAINTEXT://broker1:9092

# SASL mechanism
sasl.enabled.mechanisms=PLAIN
sasl.mechanism.inter.broker.protocol=PLAIN

# Security protocol
security.inter.broker.protocol=SASL_PLAINTEXT
```

**JAAS Configuration (kafka_server_jaas.conf):**
```
KafkaServer {
    org.apache.kafka.common.security.plain.PlainLoginModule required
    username="admin"
    password="admin-secret"
    user_admin="admin-secret"
    user_alice="alice-secret";
};
```

**Start Broker:**
```bash
export KAFKA_OPTS="-Djava.security.auth.login.config=/path/to/kafka_server_jaas.conf"
kafka-server-start.sh server.properties
```

**Client Configuration:**
```properties
bootstrap.servers=broker1:9092
security.protocol=SASL_PLAINTEXT
sasl.mechanism=PLAIN
sasl.jaas.config=org.apache.kafka.common.security.plain.PlainLoginModule required \
  username="alice" \
  password="alice-secret";
```

#### SASL/SCRAM

**Create SCRAM Credentials:**
```bash
kafka-configs.sh --bootstrap-server localhost:9092 \
  --alter --add-config 'SCRAM-SHA-256=[password=alice-secret]' \
  --entity-type users --entity-name alice

kafka-configs.sh --bootstrap-server localhost:9092 \
  --alter --add-config 'SCRAM-SHA-512=[password=alice-secret]' \
  --entity-type users --entity-name alice
```

**Broker Configuration:**
```properties
listeners=SASL_PLAINTEXT://broker1:9092
sasl.enabled.mechanisms=SCRAM-SHA-256,SCRAM-SHA-512
sasl.mechanism.inter.broker.protocol=SCRAM-SHA-256
security.inter.broker.protocol=SASL_PLAINTEXT
```

**JAAS Configuration:**
```
KafkaServer {
    org.apache.kafka.common.security.scram.ScramLoginModule required
    username="admin"
    password="admin-secret";
};
```

**Client Configuration:**
```properties
security.protocol=SASL_PLAINTEXT
sasl.mechanism=SCRAM-SHA-256
sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required \
  username="alice" \
  password="alice-secret";
```

#### SASL/GSSAPI (Kerberos)

**Broker Configuration:**
```properties
listeners=SASL_PLAINTEXT://broker1:9092
sasl.enabled.mechanisms=GSSAPI
sasl.mechanism.inter.broker.protocol=GSSAPI
security.inter.broker.protocol=SASL_PLAINTEXT
sasl.kerberos.service.name=kafka
```

**JAAS Configuration:**
```
KafkaServer {
    com.sun.security.auth.module.Krb5LoginModule required
    useKeyTab=true
    storeKey=true
    keyTab="/etc/security/keytabs/kafka_server.keytab"
    principal="kafka/broker1@REALM";
};
```

**Client Configuration:**
```properties
security.protocol=SASL_PLAINTEXT
sasl.mechanism=GSSAPI
sasl.kerberos.service.name=kafka
sasl.jaas.config=com.sun.security.auth.module.Krb5LoginModule required \
  useKeyTab=true \
  storeKey=true \
  keyTab="/etc/security/keytabs/kafka_client.keytab" \
  principal="kafka-client@REALM";
```

#### SASL/OAUTHBEARER

**Broker Configuration:**
```properties
listeners=SASL_PLAINTEXT://broker1:9092
sasl.enabled.mechanisms=OAUTHBEARER
sasl.mechanism.inter.broker.protocol=OAUTHBEARER
security.inter.broker.protocol=SASL_PLAINTEXT
```

**JAAS Configuration:**
```
KafkaServer {
    org.apache.kafka.common.security.oauthbearer.OAuthBearerLoginModule required
    unsecuredLoginStringClaim_sub="admin";
};
```

## Encryption

### SSL/TLS Encryption

**Complete SSL Configuration:**
```properties
# Listeners with SSL
listeners=SSL://broker1:9093
advertised.listeners=SSL://broker1:9093

# SSL for inter-broker
security.inter.broker.protocol=SSL

# Keystore
ssl.keystore.location=/var/private/ssl/kafka.server.keystore.jks
ssl.keystore.password=password
ssl.key.password=password

# Truststore
ssl.truststore.location=/var/private/ssl/kafka.server.truststore.jks
ssl.truststore.password=password

# SSL protocols
ssl.enabled.protocols=TLSv1.2,TLSv1.3
ssl.protocol=TLSv1.3

# Client authentication
ssl.client.auth=required

# Cipher suites
ssl.cipher.suites=TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256

# Endpoint identification
ssl.endpoint.identification.algorithm=https
```

### SASL + SSL

**Broker Configuration:**
```properties
listeners=SASL_SSL://broker1:9094
advertised.listeners=SASL_SSL://broker1:9094
security.inter.broker.protocol=SASL_SSL

# SASL
sasl.enabled.mechanisms=SCRAM-SHA-256
sasl.mechanism.inter.broker.protocol=SCRAM-SHA-256

# SSL
ssl.keystore.location=/var/private/ssl/kafka.server.keystore.jks
ssl.keystore.password=password
ssl.key.password=password
ssl.truststore.location=/var/private/ssl/kafka.server.truststore.jks
ssl.truststore.password=password
```

**Client Configuration:**
```properties
bootstrap.servers=broker1:9094
security.protocol=SASL_SSL
sasl.mechanism=SCRAM-SHA-256
sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required \
  username="alice" \
  password="alice-secret";

ssl.truststore.location=/var/private/ssl/kafka.client.truststore.jks
ssl.truststore.password=password
```

## Authorization

### ACL (Access Control Lists)

#### Enable ACLs

**Broker Configuration:**
```properties
# Authorizer class
authorizer.class.name=org.apache.kafka.metadata.authorizer.StandardAuthorizer

# Super users
super.users=User:admin;User:kafka

# Allow everyone if no ACL found (default: false)
allow.everyone.if.no.acl.found=false
```

#### ACL Operations

**Grant Permissions:**
```bash
# Producer permission
kafka-acls.sh --bootstrap-server localhost:9092 \
  --add \
  --allow-principal User:alice \
  --operation Write \
  --operation Describe \
  --operation Create \
  --topic test-topic

# Consumer permission
kafka-acls.sh --bootstrap-server localhost:9092 \
  --add \
  --allow-principal User:bob \
  --operation Read \
  --operation Describe \
  --topic test-topic \
  --group test-consumer-group

# Admin permission
kafka-acls.sh --bootstrap-server localhost:9092 \
  --add \
  --allow-principal User:admin \
  --operation All \
  --topic '*' \
  --cluster
```

**List ACLs:**
```bash
kafka-acls.sh --bootstrap-server localhost:9092 --list

# For specific topic
kafka-acls.sh --bootstrap-server localhost:9092 \
  --list --topic test-topic

# For specific principal
kafka-acls.sh --bootstrap-server localhost:9092 \
  --list --principal User:alice
```

**Remove ACLs:**
```bash
kafka-acls.sh --bootstrap-server localhost:9092 \
  --remove \
  --allow-principal User:alice \
  --operation Write \
  --topic test-topic
```

#### ACL Patterns

**Literal:**
```bash
kafka-acls.sh --add \
  --allow-principal User:alice \
  --operation Read \
  --topic orders \
  --resource-pattern-type literal
```

**Prefixed:**
```bash
kafka-acls.sh --add \
  --allow-principal User:alice \
  --operation Read \
  --topic orders- \
  --resource-pattern-type prefixed
```

**Common Permissions:**

| Operation | Description |
|-----------|-------------|
| Read | Consumer read |
| Write | Producer write |
| Create | Create topics |
| Delete | Delete topics |
| Alter | Alter topics |
| Describe | Describe topics |
| ClusterAction | Cluster operations |
| All | All operations |

### Custom Authorizer

```java
public class CustomAuthorizer implements Authorizer {

    @Override
    public void configure(Map<String, ?> configs) {
        // Initialize
    }

    @Override
    public List<AuthorizationResult> authorize(
            AuthorizableRequestContext requestContext,
            List<Action> actions) {

        // Custom authorization logic
        return actions.stream()
            .map(action -> {
                if (isAuthorized(requestContext, action)) {
                    return AuthorizationResult.ALLOWED;
                } else {
                    return AuthorizationResult.DENIED;
                }
            })
            .collect(Collectors.toList());
    }

    @Override
    public void close() {
        // Cleanup
    }

    private boolean isAuthorized(
            AuthorizableRequestContext context,
            Action action) {
        // Implement custom logic
        return true;
    }
}
```

**Configuration:**
```properties
authorizer.class.name=com.example.CustomAuthorizer
```

## Encryption at Rest

Kafka không có built-in encryption at rest. Có thể sử dụng:

### 1. File System Encryption

**Linux (LUKS):**
```bash
# Create encrypted partition
cryptsetup luksFormat /dev/sdb1

# Open encrypted partition
cryptsetup luksOpen /dev/sdb1 kafka_data

# Mount
mount /dev/mapper/kafka_data /var/lib/kafka
```

### 2. Disk Encryption

- **Cloud**: AWS EBS encryption, GCP disk encryption
- **Hardware**: Self-encrypting drives (SED)

## Quotas

### Client Quotas

**Set Producer Quota:**
```bash
kafka-configs.sh --bootstrap-server localhost:9092 \
  --alter --add-config 'producer_byte_rate=1048576' \
  --entity-type users --entity-name alice
```

**Set Consumer Quota:**
```bash
kafka-configs.sh --bootstrap-server localhost:9092 \
  --alter --add-config 'consumer_byte_rate=2097152' \
  --entity-type users --entity-name bob
```

**Request Rate Quota:**
```bash
kafka-configs.sh --bootstrap-server localhost:9092 \
  --alter --add-config 'request_percentage=50' \
  --entity-type users --entity-name alice
```

**Default Quotas:**
```bash
kafka-configs.sh --bootstrap-server localhost:9092 \
  --alter --add-config 'producer_byte_rate=1048576,consumer_byte_rate=2097152' \
  --entity-type users --entity-default
```

## Audit Logging

### Enable Audit Logs

**log4j.properties:**
```properties
# Audit logger
log4j.logger.kafka.authorizer.logger=INFO, authorizerAppender
log4j.additivity.kafka.authorizer.logger=false

# Appender
log4j.appender.authorizerAppender=org.apache.log4j.RollingFileAppender
log4j.appender.authorizerAppender.File=/var/log/kafka/kafka-authorizer.log
log4j.appender.authorizerAppender.MaxFileSize=100MB
log4j.appender.authorizerAppender.MaxBackupIndex=10
log4j.appender.authorizerAppender.layout=org.apache.log4j.PatternLayout
log4j.appender.authorizerAppender.layout.ConversionPattern=[%d] %p %m (%c)%n
```

**Log Output:**
```
[2024-01-15 10:30:45,123] INFO Principal = User:alice is Allowed Operation = Write from host = 192.168.1.100 on resource = Topic:LITERAL:orders
```

## Security Best Practices

### 1. Network Segmentation
- Isolate Kafka cluster trong private network
- Dùng firewalls để restrict access
- VPN/VPC cho remote access

### 2. Authentication
- Enable SASL authentication
- Dùng SSL/TLS cho encryption
- Rotate credentials định kỳ

### 3. Authorization
- Enable ACLs
- Principle of least privilege
- Regular audit của permissions

### 4. Encryption
- Enable SSL/TLS cho data in transit
- Encrypt disks cho data at rest
- Rotate certificates định kỳ

### 5. Monitoring
- Monitor authentication failures
- Track authorization denials
- Alert on suspicious activities

### 6. Credentials Management
- Dùng secret management systems (Vault, AWS Secrets Manager)
- Không hardcode credentials
- Rotate passwords/keys định kỳ

## Production Security Checklist

```
☐ SSL/TLS enabled cho all listeners
☐ SASL authentication configured
☐ ACLs enabled và configured
☐ Super users limited
☐ allow.everyone.if.no.acl.found=false
☐ Disk encryption enabled
☐ Audit logging enabled
☐ Quotas configured
☐ Network segmentation
☐ Firewall rules
☐ Monitoring alerts
☐ Regular security audits
☐ Credentials rotation policy
☐ Backup và disaster recovery plan
```

## Example Secure Setup

**server.properties:**
```properties
# Listeners
listeners=SASL_SSL://broker1:9094
advertised.listeners=SASL_SSL://broker1:9094
security.inter.broker.protocol=SASL_SSL

# SASL
sasl.enabled.mechanisms=SCRAM-SHA-256
sasl.mechanism.inter.broker.protocol=SCRAM-SHA-256

# SSL
ssl.keystore.location=/var/private/ssl/kafka.server.keystore.jks
ssl.keystore.password=${KEYSTORE_PASSWORD}
ssl.key.password=${KEY_PASSWORD}
ssl.truststore.location=/var/private/ssl/kafka.server.truststore.jks
ssl.truststore.password=${TRUSTSTORE_PASSWORD}
ssl.client.auth=required
ssl.enabled.protocols=TLSv1.3
ssl.endpoint.identification.algorithm=https

# Authorization
authorizer.class.name=org.apache.kafka.metadata.authorizer.StandardAuthorizer
super.users=User:admin
allow.everyone.if.no.acl.found=false

# Quotas
quota.producer.default=10485760
quota.consumer.default=20971520
```

Thiết lập security một cách đúng đắn là rất quan trọng cho production Kafka clusters!
