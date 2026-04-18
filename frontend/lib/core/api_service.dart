import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../models/user_model.dart';

class ApiService {
  // Configura la URL base del backend Flask.
  // Para emulador Android: 'http://10.0.2.2:5000'
  // Para iOS Simulator: 'http://localhost:5000'
  // Para dispositivo físico en la misma red: la IP de tu PC en la red local (ej. 'http://192.168.1.100:5000')
  // ¡Importante! Asegúrate de que tu PC y el dispositivo/emulador estén en la misma red si usas IP local.
  // Para el reto, puedes usar 'http://localhost:5000' y configurar el emulador si es necesario,
  // o usar la IP local de tu máquina si pruebas en un dispositivo físico.
  final String _baseUrl = kDebugMode ? 'http://10.0.2.2:5000' : 'http://tu_ip_produccion:5000'; // Ajusta según tu entorno

  // Método para enviar una pregunta al backend Flask
  Future<String> askQuestion(String question) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/ask'),
        headers: {
          'Content-Type': 'application/json; charset=UTF-8',
        },
        body: jsonEncode(<String, String>{
          'question': question,
        }),
      );

      if (response.statusCode == 200) {
        final Map<String, dynamic> responseData = jsonDecode(response.body);
        return responseData['respuesta'] ?? 'No se recibió una respuesta válida.';
      } else {
        // Manejar errores de la API de forma más detallada
        debugPrint('Error de API (${response.statusCode}): ${response.body}');
        if (response.statusCode == 400) {
          return 'Error: La pregunta no pudo ser procesada. Revisa tu consulta.';
        } else if (response.statusCode == 500) {
          return 'Error del servidor. Por favor, inténtalo más tarde.';
        } else {
          return 'Ocurrió un error desconocido.';
        }
      }
    } catch (e) {
      debugPrint('Excepción al hacer la llamada a la API: $e');
      return 'No se pudo conectar con el servidor. Asegúrate de que el backend esté corriendo.';
    }
  }

  // Puedes añadir otros métodos aquí si necesitas obtener datos del backend
  // Future<List<dynamic>> getTransactions() async { ... }

  // ── Login ──────────────────────────────────────────────────────────────────
  // Llama a POST /auth/login con username y password.
  // Devuelve un [UserModel] si la respuesta es 200, o lanza una [Exception]
  // con el mensaje de error para mostrarlo en la UI.
  //
  // TODO: ajustar el endpoint y los campos del JSON cuando el backend esté listo.
  Future<UserModel> login(String username, String password) async {
    // ── Placeholder mock (eliminar cuando el backend esté disponible) ──────
    if (kDebugMode) {
      await Future.delayed(const Duration(milliseconds: 800)); // simula latencia
      if (username.trim().isEmpty || password.length < 4) {
        throw Exception('Usuario o contraseña incorrectos.');
      }
      return UserModel(
        username: username.trim(),
        fullName: '${username.trim()} Usuario Placeholder',
        role: 'Admin',
        token: 'mock-token-dev-only',
      );
    }
    // ── Llamada real al backend ────────────────────────────────────────────
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/auth/login'),
        headers: {'Content-Type': 'application/json; charset=UTF-8'},
        body: jsonEncode({
          'username': username.trim(),
          'password': password,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return UserModel.fromJson(data);
      } else if (response.statusCode == 401) {
        throw Exception('Usuario o contraseña incorrectos.');
      } else {
        throw Exception('Error del servidor (${response.statusCode}). Intenta más tarde.');
      }
    } catch (e) {
      if (e is Exception) rethrow;
      throw Exception('No se pudo conectar al servidor.');
    }
  }
}