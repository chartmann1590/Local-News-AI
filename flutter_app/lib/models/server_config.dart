import '../utils/constants.dart';

class ServerConfig {
  final String ip;
  final String port;
  
  ServerConfig({
    required this.ip,
    required this.port,
  });
  
  String get baseUrl {
    // Ensure protocol is included
    String protocol = ip.startsWith('http') ? '' : 'http://';
    String cleanIp = ip.replaceAll('http://', '').replaceAll('https://', '');
    return '$protocol$cleanIp:$port';
  }
  
  String get healthUrl => '$baseUrl${Constants.healthEndpoint}';
  
  Map<String, dynamic> toJson() {
    return {
      'ip': ip,
      'port': port,
    };
  }
  
  factory ServerConfig.fromJson(Map<String, dynamic> json) {
    return ServerConfig(
      ip: json['ip'] as String,
      port: json['port'] as String,
    );
  }
  
  @override
  String toString() => baseUrl;
}

