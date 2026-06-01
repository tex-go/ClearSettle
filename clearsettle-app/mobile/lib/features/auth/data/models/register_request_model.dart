class RegisterRequestModel {
  const RegisterRequestModel({
    required this.name,
    required this.email,
    required this.phone,
    required this.password,
    required this.confirmPassword,
    required this.companyName,
    required this.state,
    required this.role,
    this.gstin,
    this.city,
  });

  final String name;
  final String email;
  final String phone;
  final String password;
  final String confirmPassword;
  final String companyName;
  final String state;
  final String role;
  final String? gstin;
  final String? city;

  Map<String, dynamic> toJson() => {
        'name': name,
        'email': email,
        'phone': phone,
        'password': password,
        'confirm_password': confirmPassword,
        'company_name': companyName,
        'state': state,
        'role': role,
        if (gstin != null && gstin!.isNotEmpty) 'gstin': gstin,
        if (city != null && city!.isNotEmpty) 'city': city,
        'active_platforms': [],
      };
}

class RegistrationRoleModel {
  const RegistrationRoleModel({
    required this.id,
    required this.name,
    required this.description,
    required this.icon,
  });

  final String id;
  final String name;
  final String description;
  final String icon;

  factory RegistrationRoleModel.fromJson(Map<String, dynamic> json) {
    return RegistrationRoleModel(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String,
      icon: (json['icon'] as String?) ?? 'person',
    );
  }
}
