class UserModel {
  final String username;
  final String fullName;
  final String role;
  final String token;

  const UserModel({
    required this.username,
    required this.fullName,
    required this.role,
    required this.token,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      username: json['username'] as String? ?? '',
      fullName: json['full_name'] as String? ?? '',
      role: json['role'] as String? ?? 'Usuario',
      token: json['token'] as String? ?? '',
    );
  }

  /// Nombre abreviado para mostrar en el header (máx. 20 chars + "...")
  String get displayName {
    if (fullName.length <= 22) return fullName;
    return '${fullName.substring(0, 22)}...';
  }

  /// Primer nombre para el saludo
  String get firstName {
    final parts = fullName.trim().split(' ');
    return parts.isNotEmpty ? parts.first : username;
  }
}
