# Apache Kafka Documentation

## Tổng quan

Apache Kafka là một nền tảng streaming phân tán (distributed streaming platform) mã nguồn mở được phát triển bởi Apache Software Foundation. Kafka được thiết kế để xử lý luồng dữ liệu thời gian thực với khả năng mở rộng cao, độ tin cậy và hiệu suất tốt.

## Mục đích sử dụng

Kafka được sử dụng để:

1. **Messaging System**: Xây dựng hệ thống tin nhắn thời gian thực giữa các ứng dụng
2. **Stream Processing**: Xử lý và phân tích luồng dữ liệu theo thời gian thực
3. **Event Sourcing**: Lưu trữ và theo dõi các sự kiện trong hệ thống
4. **Log Aggregation**: Thu thập và tổng hợp log từ nhiều nguồn khác nhau
5. **Metrics Collection**: Thu thập và theo dõi các chỉ số hệ thống

## Đặc điểm chính

### 1. Hiệu suất cao (High Throughput)
- Xử lý hàng triệu messages/giây
- Độ trễ thấp (milliseconds)
- Khả năng mở rộng theo chiều ngang

### 2. Khả năng mở rộng (Scalability)
- Dễ dàng thêm broker vào cluster
- Tự động phân phối lại partitions
- Hỗ trợ hàng nghìn producers và consumers

### 3. Độ tin cậy (Durability)
- Lưu trữ dữ liệu trên đĩa
- Replication giữa các broker
- Đảm bảo không mất dữ liệu

### 4. Khả năng chịu lỗi (Fault Tolerance)
- Tự động phục hồi khi broker gặp sự cố
- Leader election tự động
- Data replication

## Các thành phần chính

1. **Producer**: Ứng dụng gửi dữ liệu vào Kafka
2. **Consumer**: Ứng dụng đọc dữ liệu từ Kafka
3. **Broker**: Server lưu trữ và quản lý dữ liệu
4. **Topic**: Danh mục để tổ chức dữ liệu
5. **Partition**: Phân đoạn của topic để tăng hiệu suất
6. **ZooKeeper/KRaft**: Quản lý và điều phối cluster

## Use Cases phổ biến

- **Website Activity Tracking**: Theo dõi hành vi người dùng
- **Metrics & Monitoring**: Thu thập metrics từ các ứng dụng
- **Log Aggregation**: Tổng hợp log từ nhiều service
- **Stream Processing**: Xử lý dữ liệu real-time với Kafka Streams
- **Event Sourcing**: Lưu trữ event history
- **Commit Log**: Sao lưu và đồng bộ dữ liệu giữa các hệ thống

## Nội dung Documentation

Tài liệu này bao gồm các phần sau:

1. [Kiến trúc Kafka](./architecture.md)
2. [Các khái niệm cơ bản](./core-concepts.md)
3. [Producers và Consumers](./producers-consumers.md)
4. [Kafka Streams](./streams.md)
5. [Kafka Connect](./connect.md)
6. [Hướng dẫn bắt đầu](./getting-started.md)
7. [Cấu hình và tối ưu](./configuration.md)
8. [Security](./security.md)

## Phiên bản

Tài liệu này được cập nhật cho Apache Kafka phiên bản 3.x trở lên, bao gồm các tính năng mới nhất như KRaft mode (thay thế ZooKeeper).

## Tham khảo

- [Apache Kafka Official Documentation](https://kafka.apache.org/documentation/)
- [Confluent Documentation](https://docs.confluent.io/)
- [Kafka GitHub Repository](https://github.com/apache/kafka)
