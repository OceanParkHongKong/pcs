// utils.dart
import 'dart:html' as html;

Uri getServerUrl(String path, {Map<String, String>? queryParams}) {
  final uri = html.window.location;
  // Get the host IP address dynamically
  final host = uri.hostname?.isNotEmpty == true ? uri.hostname : '127.0.0.1';
  final port = int.tryParse(uri.port) ?? 80; // Convert to int, default to 80 if null
  final scheme = uri.protocol.replaceFirst(':', ''); // 'http' or 'https'

  return Uri(
    scheme: scheme,
    host: host,
    // port: port, //for release
    port: 8000,//for debug flutter
    path: path,
    queryParameters: queryParams,
  );
}