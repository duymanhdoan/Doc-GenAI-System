# Kafka Connect

## Tổng quan

**Kafka Connect** là framework để streaming data giữa Apache Kafka và các hệ thống khác một cách đáng tin cậy và có khả năng mở rộng.

## Đặc điểm chính

### 1. Pluggable Architecture
- Hỗ trợ nhiều connectors
- Dễ dàng thêm connectors mới
- Community ecosystem lớn

### 2. Distributed và Standalone Mode
- **Standalone**: Chạy trên 1 process (dev/test)
- **Distributed**: Cluster có khả năng mở rộng (production)

### 3. Fault Tolerance
- Tự động recovery
- Offset management
- Exactly-once semantics

### 4. Scalability
- Scale horizontally
- Parallel task execution
- Load balancing

## Architecture

```
┌─────────────────────────────────────────────────┐
│           External Systems                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │   MySQL  │  │ MongoDB  │  │   S3     │      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│       │             │             │             │
└───────┼─────────────┼─────────────┼─────────────┘
        │             │             │
    ┌───▼─────────────▼─────────────▼───┐
    │    Kafka Connect Cluster          │
    │  ┌─────────────────────────────┐  │
    │  │  Source Connectors          │  │
    │  │  - JDBC, Debezium, etc.     │  │
    │  └──────────────┬──────────────┘  │
    │                 │                  │
    │  ┌──────────────▼──────────────┐  │
    │  │    Workers                  │  │
    │  │  - Task management          │  │
    │  │  - Offset storage           │  │
    │  │  - Config management        │  │
    │  └──────────────┬──────────────┘  │
    │                 │                  │
    │  ┌──────────────▼──────────────┐  │
    │  │  Sink Connectors            │  │
    │  │  - Elasticsearch, HDFS      │  │
    │  └─────────────────────────────┘  │
    └─────────────────┬─────────────────┘
                      │
              ┌───────▼────────┐
              │  Kafka Cluster │
              └────────────────┘
```

## Core Concepts

### 1. Connector
Plugin định nghĩa cách connect với external system.

### 2. Task
Đơn vị thực thi công việc (copying data).

### 3. Worker
Process chạy connectors và tasks.

### 4. Converter
Chuyển đổi data giữa Kafka và external system.

### 5. Transform
Modification đơn giản của messages.

## Setup

### Standalone Mode

**worker.properties:**
```properties
bootstrap.servers=localhost:9092

# Offset storage (file-based for standalone)
offset.storage.file.filename=/tmp/connect.offsets

# Converters
key.converter=org.apache.kafka.connect.json.JsonConverter
value.converter=org.apache.kafka.connect.json.JsonConverter
key.converter.schemas.enable=false
value.converter.schemas.enable=false

# Plugin path
plugin.path=/usr/local/share/kafka/plugins
```

**Start standalone:**
```bash
connect-standalone.sh worker.properties connector.properties
```

### Distributed Mode

**worker.properties:**
```properties
bootstrap.servers=localhost:9092

# Group ID
group.id=connect-cluster

# Offset/Config/Status storage topics
offset.storage.topic=connect-offsets
offset.storage.replication.factor=3
config.storage.topic=connect-configs
config.storage.replication.factor=3
status.storage.topic=connect-status
status.storage.replication.factor=3

# Converters
key.converter=org.apache.kafka.connect.json.JsonConverter
value.converter=org.apache.kafka.connect.json.JsonConverter

# REST API
rest.port=8083

# Plugin path
plugin.path=/usr/local/share/kafka/plugins
```

**Start distributed:**
```bash
connect-distributed.sh worker.properties
```

## Source Connectors

Source connectors import data từ external systems vào Kafka.

### JDBC Source Connector

**Configuration:**
```json
{
  "name": "mysql-source",
  "config": {
    "connector.class": "io.confluent.connect.jdbc.JdbcSourceConnector",
    "tasks.max": "1",
    "connection.url": "jdbc:mysql://localhost:3306/mydb",
    "connection.user": "user",
    "connection.password": "password",
    "table.whitelist": "users,orders",
    "mode": "incrementing",
    "incrementing.column.name": "id",
    "topic.prefix": "mysql-",
    "poll.interval.ms": "1000"
  }
}
```

**Modes:**
- **Incrementing**: Dựa vào cột tăng dần (id)
- **Timestamp**: Dựa vào timestamp column
- **Timestamp+Incrementing**: Kết hợp cả hai
- **Bulk**: Load toàn bộ table

### Debezium CDC Connector

**Configuration:**
```json
{
  "name": "mysql-cdc",
  "config": {
    "connector.class": "io.debezium.connector.mysql.MySqlConnector",
    "tasks.max": "1",
    "database.hostname": "localhost",
    "database.port": "3306",
    "database.user": "debezium",
    "database.password": "password",
    "database.server.id": "184054",
    "database.server.name": "mysql-server",
    "database.include.list": "mydb",
    "table.include.list": "mydb.users,mydb.orders",
    "database.history.kafka.bootstrap.servers": "localhost:9092",
    "database.history.kafka.topic": "dbhistory.mysql"
  }
}
```

### File Source Connector

```json
{
  "name": "file-source",
  "config": {
    "connector.class": "FileStreamSource",
    "tasks.max": "1",
    "file": "/var/log/app.log",
    "topic": "app-logs"
  }
}
```

## Sink Connectors

Sink connectors export data từ Kafka ra external systems.

### JDBC Sink Connector

```json
{
  "name": "postgres-sink",
  "config": {
    "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
    "tasks.max": "1",
    "connection.url": "jdbc:postgresql://localhost:5432/mydb",
    "connection.user": "user",
    "connection.password": "password",
    "topics": "orders",
    "auto.create": "true",
    "auto.evolve": "true",
    "insert.mode": "upsert",
    "pk.mode": "record_key",
    "pk.fields": "id"
  }
}
```

### Elasticsearch Sink Connector

```json
{
  "name": "elasticsearch-sink",
  "config": {
    "connector.class": "io.confluent.connect.elasticsearch.ElasticsearchSinkConnector",
    "tasks.max": "1",
    "topics": "logs",
    "connection.url": "http://localhost:9200",
    "type.name": "_doc",
    "key.ignore": "false",
    "schema.ignore": "true"
  }
}
```

### S3 Sink Connector

```json
{
  "name": "s3-sink",
  "config": {
    "connector.class": "io.confluent.connect.s3.S3SinkConnector",
    "tasks.max": "1",
    "topics": "events",
    "s3.bucket.name": "my-bucket",
    "s3.region": "us-east-1",
    "flush.size": "1000",
    "storage.class": "io.confluent.connect.s3.storage.S3Storage",
    "format.class": "io.confluent.connect.s3.format.json.JsonFormat",
    "partitioner.class": "io.confluent.connect.storage.partitioner.TimeBasedPartitioner",
    "path.format": "'year'=YYYY/'month'=MM/'day'=dd/'hour'=HH",
    "partition.duration.ms": "3600000",
    "timezone": "UTC"
  }
}
```

## REST API

### Connector Management

**List connectors:**
```bash
curl http://localhost:8083/connectors
```

**Create connector:**
```bash
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @connector-config.json
```

**Get connector status:**
```bash
curl http://localhost:8083/connectors/mysql-source/status
```

**Pause connector:**
```bash
curl -X PUT http://localhost:8083/connectors/mysql-source/pause
```

**Resume connector:**
```bash
curl -X PUT http://localhost:8083/connectors/mysql-source/resume
```

**Delete connector:**
```bash
curl -X DELETE http://localhost:8083/connectors/mysql-source
```

**Update connector:**
```bash
curl -X PUT http://localhost:8083/connectors/mysql-source/config \
  -H "Content-Type: application/json" \
  -d @new-config.json
```

**Restart connector:**
```bash
curl -X POST http://localhost:8083/connectors/mysql-source/restart
```

**Get tasks:**
```bash
curl http://localhost:8083/connectors/mysql-source/tasks
```

**Restart task:**
```bash
curl -X POST http://localhost:8083/connectors/mysql-source/tasks/0/restart
```

## Converters

### JSON Converter

```properties
key.converter=org.apache.kafka.connect.json.JsonConverter
value.converter=org.apache.kafka.connect.json.JsonConverter
key.converter.schemas.enable=true
value.converter.schemas.enable=true
```

### Avro Converter

```properties
key.converter=io.confluent.connect.avro.AvroConverter
value.converter=io.confluent.connect.avro.AvroConverter
key.converter.schema.registry.url=http://localhost:8081
value.converter.schema.registry.url=http://localhost:8081
```

### String Converter

```properties
key.converter=org.apache.kafka.connect.storage.StringConverter
value.converter=org.apache.kafka.connect.storage.StringConverter
```

### ByteArray Converter

```properties
key.converter=org.apache.kafka.connect.converters.ByteArrayConverter
value.converter=org.apache.kafka.connect.converters.ByteArrayConverter
```

## Single Message Transforms (SMT)

SMTs modify messages khi chúng đi qua connector.

### Common Transforms

#### 1. Insert Field

```json
{
  "transforms": "insertSource",
  "transforms.insertSource.type": "org.apache.kafka.connect.transforms.InsertField$Value",
  "transforms.insertSource.static.field": "source",
  "transforms.insertSource.static.value": "database"
}
```

#### 2. Replace Field

```json
{
  "transforms": "renameField",
  "transforms.renameField.type": "org.apache.kafka.connect.transforms.ReplaceField$Value",
  "transforms.renameField.renames": "old_name:new_name"
}
```

#### 3. Mask Field

```json
{
  "transforms": "maskField",
  "transforms.maskField.type": "org.apache.kafka.connect.transforms.MaskField$Value",
  "transforms.maskField.fields": "password,ssn"
}
```

#### 4. Filter

```json
{
  "transforms": "filter",
  "transforms.filter.type": "io.confluent.connect.transforms.Filter$Value",
  "transforms.filter.condition": "$.status == 'active'"
}
```

#### 5. Timestamp Router

```json
{
  "transforms": "TimestampRouter",
  "transforms.TimestampRouter.type": "org.apache.kafka.connect.transforms.TimestampRouter",
  "transforms.TimestampRouter.topic.format": "${topic}-${timestamp}",
  "transforms.TimestampRouter.timestamp.format": "yyyyMMdd"
}
```

### Chain Transforms

```json
{
  "transforms": "insertSource,addTimestamp,renameField",
  "transforms.insertSource.type": "...",
  "transforms.addTimestamp.type": "...",
  "transforms.renameField.type": "..."
}
```

## Custom Connector

### Source Connector Example

```java
public class MySourceConnector extends SourceConnector {
    private Map<String, String> config;

    @Override
    public void start(Map<String, String> props) {
        this.config = props;
    }

    @Override
    public Class<? extends Task> taskClass() {
        return MySourceTask.class;
    }

    @Override
    public List<Map<String, String>> taskConfigs(int maxTasks) {
        List<Map<String, String>> configs = new ArrayList<>();
        for (int i = 0; i < maxTasks; i++) {
            configs.add(config);
        }
        return configs;
    }

    @Override
    public void stop() {
        // Cleanup
    }

    @Override
    public ConfigDef config() {
        return new ConfigDef()
            .define("my.config", ConfigDef.Type.STRING,
                    ConfigDef.Importance.HIGH, "My config");
    }

    @Override
    public String version() {
        return "1.0.0";
    }
}
```

### Source Task Example

```java
public class MySourceTask extends SourceTask {
    @Override
    public void start(Map<String, String> props) {
        // Initialize
    }

    @Override
    public List<SourceRecord> poll() throws InterruptedException {
        List<SourceRecord> records = new ArrayList<>();

        // Fetch data from source
        Data data = fetchData();

        SourceRecord record = new SourceRecord(
            sourcePartition(),
            sourceOffset(),
            "my-topic",
            Schema.STRING_SCHEMA,
            data.getKey(),
            Schema.STRING_SCHEMA,
            data.getValue()
        );

        records.add(record);
        return records;
    }

    @Override
    public void stop() {
        // Cleanup
    }

    @Override
    public String version() {
        return "1.0.0";
    }
}
```

## Best Practices

### 1. Configuration

```properties
# Worker configuration
tasks.max=4
offset.flush.interval.ms=10000
offset.flush.timeout.ms=5000

# Error handling
errors.tolerance=all
errors.log.enable=true
errors.log.include.messages=true
errors.deadletterqueue.topic.name=dlq-topic
```

### 2. Monitoring

Monitor these metrics:
- Connector status
- Task status
- Offset lag
- Throughput
- Error rate

### 3. Scaling

- Increase `tasks.max`
- Add more workers
- Partition source data

### 4. Error Handling

```json
{
  "errors.tolerance": "all",
  "errors.log.enable": "true",
  "errors.deadletterqueue.topic.name": "dlq",
  "errors.deadletterqueue.topic.replication.factor": "3",
  "errors.deadletterqueue.context.headers.enable": "true"
}
```

### 5. Performance Tuning

```properties
# Batch size
consumer.max.poll.records=500
producer.batch.size=16384

# Buffer
producer.buffer.memory=33554432

# Compression
producer.compression.type=snappy
```

## Common Use Cases

1. **Database Replication**: Sync databases qua Kafka
2. **Data Lake Ingestion**: Stream data vào S3, HDFS
3. **Search Indexing**: Real-time index vào Elasticsearch
4. **Cache Synchronization**: Sync cache từ database changes
5. **Analytics Pipeline**: Feed data vào analytics systems
