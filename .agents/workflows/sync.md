---
description: Sincroniza el repositorio local con GitHub (git add, commit, push). Usa este comando para guardar y subir cambios al remoto.
---

# Sincronización con GitHub

Automatiza el proceso de commit y push al repositorio remoto.

## Pasos

// turbo
1. **Verificar estado del repositorio**:
   ```bash
   cd e:\Pruba antigravity\sky-claw
   git status
   ```

// turbo
2. **Revisar los cambios pendientes** (diff resumido):
   ```bash
   cd e:\Pruba antigravity\sky-claw
   git diff --stat
   ```

3. **Agregar todos los cambios al staging**:
   ```bash
   cd e:\Pruba antigravity\sky-claw
   git add -A
   ```

4. **Crear commit con mensaje descriptivo** — generar un mensaje basado en los archivos modificados:
   ```bash
   cd e:\Pruba antigravity\sky-claw
   git commit -m "<mensaje descriptivo basado en los cambios>"
   ```

5. **Push al remoto (origin main)**:
   ```bash
   cd e:\Pruba antigravity\sky-claw
   git push origin main
   ```

// turbo
6. **Verificar sincronización exitosa**:
   ```bash
   cd e:\Pruba antigravity\sky-claw
   git log -n 1 --oneline
   ```

## Notas

- Si hay conflictos de merge, resolverlos manualmente antes de continuar.
- Nunca hacer force push sin confirmación explícita del usuario.
- El mensaje de commit debe ser descriptivo y en inglés (convención del proyecto).
