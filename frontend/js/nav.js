document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("menuToggle");
  const links = document.getElementById("navLinks");
  if (toggle && links) {
    toggle.addEventListener("click", () => links.classList.toggle("open"));
  }

  // Mostrar usuario / logout si hay sesión
  const user = typeof getUsuario === "function" ? getUsuario() : null;
  const slot = document.getElementById("navUser");
  if (slot) {
    if (user) {
      slot.innerHTML = `
        <span style="font-size:0.9rem;color:#64748b;">Hola, ${user.nombre.split(" ")[0]}</span>
        <a href="/panel">Mi panel</a>
        <a href="#" id="btnLogout">Salir</a>
      `;
      document.getElementById("btnLogout")?.addEventListener("click", (e) => {
        e.preventDefault();
        clearSession();
        window.location.href = "/";
      });
    } else {
      slot.innerHTML = `
        <a href="/login">Iniciar sesión</a>
        <a href="/registro" class="nav-cta">Registrarse</a>
      `;
    }
  }
});
