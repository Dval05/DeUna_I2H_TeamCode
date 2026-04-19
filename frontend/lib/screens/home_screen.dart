import 'package:flutter/material.dart';
import '../models/user_model.dart';
import 'chat_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.user});

  final UserModel user;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen>
    with SingleTickerProviderStateMixin {
  static const Color _brandColor = Color(0xFF5B21B6);

  late TabController _tabController;
  bool _balanceVisible = false;
  int _selectedNav = 0;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this, initialIndex: 1);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Column(
          children: [
            _buildHeader(),
            _buildTabBar(),
            Expanded(
              child: TabBarView(
                controller: _tabController,
                children: [
                  _buildTabContent(),
                  _buildTabContent(),
                  _buildAsistenteTab(context),
                ],
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: _buildBottomNav(),
      floatingActionButton: _buildChatFabConditional(context),
    );
  }

  // --- Header --------------------------------------------------------------
  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 10),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: _brandColor.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.storefront_rounded,
                color: Color(0xFF5B21B6), size: 26),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text(
                      'Hola! ',
                      style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF1F2937)),
                    ),
                    Text(
                      widget.user.firstName,
                      style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF1F2937)),
                    ),
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: _brandColor,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        widget.user.role,
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 11,
                            fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  widget.user.displayName,
                  style:
                      TextStyle(color: const Color(0xFF9E9E9E), fontSize: 12),
                ),
              ],
            ),
          ),
          const Icon(Icons.qr_code_scanner_rounded,
              color: Colors.black87, size: 24),
          const SizedBox(width: 18),
          const Icon(Icons.notifications_none_rounded,
              color: Colors.black87, size: 24),
          const SizedBox(width: 18),
          const Icon(Icons.headset_mic_outlined,
              color: Colors.black87, size: 24),
        ],
      ),
    );
  }

  // --- Tabs ----------------------------------------------------------------
  Widget _buildTabBar() {
    return TabBar(
      controller: _tabController,
      labelColor: _brandColor,
      unselectedLabelColor: Colors.grey.shade500,
      indicatorColor: _brandColor,
      indicatorWeight: 2.5,
      labelStyle: const TextStyle(
          fontWeight: FontWeight.w600, fontSize: 15),
      unselectedLabelStyle: const TextStyle(
          fontWeight: FontWeight.w400, fontSize: 15),
      isScrollable: true,
      tabAlignment: TabAlignment.start,
      tabs: const [
        Tab(text: 'Cobrar'),
        Tab(text: 'Gestionar'),
        Tab(text: 'Mi asistente de bolsillo'),
      ],
    );
  }

  Widget _buildTabContent() {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildBalanceCard(),
          const SizedBox(height: 28),
          _buildAccesosRapidos(),
          const SizedBox(height: 28),
          _buildNovedades(),
          const SizedBox(height: 80),
        ],
      ),
    );
  }

  // --- Tarjeta saldo -------------------------------------------------------
  Widget _buildBalanceCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border(
            left: BorderSide(color: _brandColor.withValues(alpha: 0.6), width: 3)),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withValues(alpha: 0.06),
              blurRadius: 8,
              offset: const Offset(0, 2)),
        ],
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Mi Saldo',
                    style: TextStyle(
                        color: Colors.grey.shade500, fontSize: 13)),
                const SizedBox(height: 8),
                Row(
                  children: [
                    const Text(
                      '\$  ',
                      style: TextStyle(
                          fontSize: 22, fontWeight: FontWeight.bold),
                    ),
                    Text(
                      _balanceVisible ? '1,234.56' : '*****',
                      style: const TextStyle(
                          fontSize: 22, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(width: 10),
                    GestureDetector(
                      onTap: () =>
                          setState(() => _balanceVisible = !_balanceVisible),
                      child: Icon(
                        _balanceVisible
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined,
                        size: 22,
                        color: Colors.black87,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const Icon(Icons.chevron_right_rounded,
              size: 26, color: Colors.black54),
        ],
      ),
    );
  }

  // --- Accesos rapidos -----------------------------------------------------
  Widget _buildAccesosRapidos() {
    final items = [
      (Icons.arrow_downward_rounded, 'Recargar\nsaldo'),
      (Icons.arrow_upward_rounded, 'Transferir\nsaldo'),
      (Icons.attach_money_rounded, 'Venta\nManual'),
      (Icons.verified_outlined, 'Verificar\npago'),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Accesos rápidos',
          style: TextStyle(
              fontSize: 17,
              fontWeight: FontWeight.bold,
              color: Color(0xFF1F2937)),
        ),
        const SizedBox(height: 16),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children:
              items.map((e) => _accesoItem(e.$1, e.$2)).toList(),
        ),
      ],
    );
  }

  Widget _accesoItem(IconData icon, String label) {
    return Column(
      children: [
        Container(
          width: 62,
          height: 62,
          decoration: const BoxDecoration(
            color: Color(0xFFF3F4F6),
            shape: BoxShape.circle,
          ),
          child: Icon(icon, size: 26, color: const Color(0xFF1F2937)),
        ),
        const SizedBox(height: 8),
        Text(
          label,
          textAlign: TextAlign.center,
          style: const TextStyle(
              fontSize: 12, color: Color(0xFF374151), height: 1.3),
        ),
      ],
    );
  }

  // --- Novedades -----------------------------------------------------------
  Widget _buildNovedades() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Novedades Deuna Negocios',
          style: TextStyle(
              fontSize: 17,
              fontWeight: FontWeight.bold,
              color: Color(0xFF1F2937)),
        ),
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
                child: _novedadCard('Agrega vendedores a tu equipo')),
            const SizedBox(width: 12),
            Expanded(
                child:
                    _novedadCard('Administra tus ventas con tu caja')),
          ],
        ),
      ],
    );
  }

  Widget _novedadCard(String text) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF9FAFB),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            text,
            style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: Color(0xFF1F2937),
                height: 1.4),
          ),
          const SizedBox(height: 16),
          Container(
            width: 60,
            height: 42,
            decoration: BoxDecoration(
              color: const Color(0xFF0F766E),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Center(
              child: Text(
                'd!',
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    fontStyle: FontStyle.italic),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // --- Bottom nav ----------------------------------------------------------
  Widget _buildBottomNav() {
    return BottomNavigationBar(
      currentIndex: _selectedNav,
      onTap: (i) => setState(() => _selectedNav = i),
      selectedItemColor: _brandColor,
      unselectedItemColor: Colors.grey.shade500,
      showUnselectedLabels: true,
      type: BottomNavigationBarType.fixed,
      elevation: 8,
      items: const [
        BottomNavigationBarItem(
            icon: Icon(Icons.home_rounded), label: 'Inicio'),
        BottomNavigationBarItem(
            icon: Icon(Icons.point_of_sale_rounded), label: 'Mi Caja'),
        BottomNavigationBarItem(
          icon: Icon(Icons.menu_rounded), label: 'Menu'),
      ],
    );
  }


  // ── Tab asistente de bolsillo ─────────────────────────────────────────────
  Widget _buildAsistenteTab(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 28),
      child: Column(
        children: [
          Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              color: _brandColor.withValues(alpha: 0.08),
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.smart_toy_rounded,
              size: 40,
              color: _brandColor,
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'Asistente de bolsillo',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: Color(0xFF1F2937),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Tu guia inteligente dentro de DeUna Negocios',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 13, color: Colors.grey.shade500),
          ),
          const SizedBox(height: 24),
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: const Color(0xFFF9FAFB),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFE5E7EB)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: _brandColor.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(Icons.info_outline_rounded,
                          size: 16, color: _brandColor),
                    ),
                    const SizedBox(width: 10),
                    const Text(
                      'Aviso importante',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                        color: Color(0xFF1F2937),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                _disclaimerItem(Icons.psychology_outlined,
                    'Este asistente es un chatbot de IA para orientarte en el uso de DeUna Negocios.'),
                const SizedBox(height: 10),
                _disclaimerItem(Icons.update_rounded,
                    'Las respuestas son automaticas y pueden no reflejar informacion en tiempo real.'),
                const SizedBox(height: 10),
                _disclaimerItem(Icons.lock_outline_rounded,
                    'No compartas contrasenas, PINs ni informacion bancaria confidencial.'),
                const SizedBox(height: 10),
                _disclaimerItem(Icons.support_agent_rounded,
                    'Para soporte oficial, usa los canales autorizados de DeUna.'),
              ],
            ),
          ),
          const Spacer(),
          SizedBox(
            width: double.infinity,
            height: 52,
            child: ElevatedButton.icon(
              onPressed: () => Navigator.of(context).push(
                PageRouteBuilder(
                  pageBuilder: (context, animation, secondaryAnimation) =>
                      const ChatScreen(),
                  transitionsBuilder: (
                    context,
                    animation,
                    secondaryAnimation,
                    child,
                  ) =>
                      SlideTransition(
                        position: Tween<Offset>(
                                begin: const Offset(0, 1), end: Offset.zero)
                            .animate(CurvedAnimation(
                                parent: animation, curve: Curves.easeOut)),
                        child: child,
                      ),
                  transitionDuration: const Duration(milliseconds: 350),
                ),
              ),
              icon: const Icon(Icons.check_circle_outline_rounded,
                  color: Colors.white, size: 20),
              label: const Text(
                'Acepto, ir al asistente',
                style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: Colors.white),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: _brandColor,
                elevation: 0,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
            ),
          ),
          const SizedBox(height: 8),
        ],
      ),
    );
  }

  Widget _disclaimerItem(IconData icon, String text) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 16, color: _brandColor),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            text,
            style: const TextStyle(
              fontSize: 13,
              color: Color(0xFF4B5563),
              height: 1.45,
            ),
          ),
        ),
      ],
    );
  }

  // ── Chat FAB condicional (oculto en pestana asistente) ────────────────────
  Widget? _buildChatFabConditional(BuildContext context) {
    return ListenableBuilder(
      listenable: _tabController,
      builder: (context, child) {
        if (_tabController.index == 2) return const SizedBox.shrink();
        return _buildChatFab(context);
      },
    );
  }

  // --- Chat FAB ------------------------------------------------------------
  Widget _buildChatFab(BuildContext context) {
    return FloatingActionButton(
      backgroundColor: _brandColor,
      onPressed: () => Navigator.of(context).push(
        PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) =>
              const ChatScreen(),
          transitionsBuilder: (
            context,
            animation,
            secondaryAnimation,
            child,
          ) => SlideTransition(
            position: Tween<Offset>(
                    begin: const Offset(0, 1), end: Offset.zero)
                .animate(CurvedAnimation(
                    parent: animation, curve: Curves.easeOut)),
            child: child,
          ),
          transitionDuration: const Duration(milliseconds: 350),
        ),
      ),
      child: const Icon(Icons.chat_bubble_rounded, color: Colors.white),
    );
  }
}
