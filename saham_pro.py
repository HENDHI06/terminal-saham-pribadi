# --- 0. FUNGSI DATABASE USER (PINDAH KE GSHEETS AGAR PERMANEN) ---
def load_users_gsheet():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="users", ttl=0).dropna(how='all')
        return df
    except:
        # Jika sheet 'users' belum ada, buat default admin
        return pd.DataFrame([{"username": "admin", "password": "admin123", "role": "admin"}])

def save_users_gsheet(df):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(worksheet="users", data=df)

# --- MODIFIKASI LOGIN AGAR CEK KE GSHEETS ---
def check_login_gsheet(u, p):
    df = load_users_gsheet()
    user_row = df[(df['username'] == u) & (df['password'] == str(p))]
    if not user_row.empty:
        return user_row.iloc[0]['role']
    return None

# --- MODIFIKASI UPDATE PASSWORD (KE GSHEETS) ---
def update_password_gsheet(u, new_p):
    df = load_users_gsheet()
    if u in df['username'].values:
        df.loc[df['username'] == u, 'password'] = str(new_p)
        save_users_gsheet(df)
        return True
    return False

# --- 1. HALAMAN LOGIN (DIUBAH KE GSHEET) ---
if not st.session_state["auth"]["logged_in"]:
    _, col2, _ = st.columns([1,1.5,1])
    with col2:
        st.markdown("<div style='text-align:center; padding:50px 0;'><h1>IDX</h1><p>CYBER TERMINAL</p></div>", unsafe_allow_html=True)
        with st.form("login_form"):
            u = st.text_input("OPERATOR ID").strip()
            p = st.text_input("ACCESS KEY", type="password")
            if st.form_submit_button("AUTHORIZE ACCESS", width="stretch"):
                role = check_login_gsheet(u, p) # Cek ke GSheet
                if role:
                    st.session_state["auth"] = {"logged_in": True, "user": u, "role": role}
                    st.rerun()
                else:
                    st.error("ACCESS DENIED: Password Salah atau User Tidak Terdaftar")
    st.stop()

# --- 2. MENU USER MANAGEMENT (TAMBAH/HAPUS DI GSHEETS) ---
elif menu == "USER MANAGEMENT":
    st.title("👤 ACCESS_CONTROL")
    df_u = load_users_gsheet()
    st.dataframe(df_u, use_container_width=True, hide_index=True)
    
    col_add, col_del = st.columns(2)
    with col_add:
        with st.form("add_u"):
            st.subheader("➕ Add Operator")
            nu = st.text_input("New ID")
            np = st.text_input("New Key")
            nr = st.selectbox("Role", ["user", "admin"])
            if st.form_submit_button("GRANT ACCESS"):
                if nu and np:
                    new_user = pd.DataFrame([{"username": nu, "password": np, "role": nr}])
                    df_u = pd.concat([df_u, new_user], ignore_index=True)
                    save_users_gsheet(df_u)
                    st.success(f"User {nu} Berhasil Disimpan di GSheets")
                    st.rerun()

    with col_del:
        st.subheader("🔴 Revoke Access")
        du = st.text_input("Target ID to Delete")
        if st.button("EXECUTE DELETION"):
            if du != 'admin':
                df_u = df_u[df_u['username'] != du]
                save_users_gsheet(df_u)
                st.warning(f"User {du} Dihapus")
                st.rerun()
            else:
                st.error("Admin utama tidak bisa dihapus!")

# --- 3. MENU SECURITY SETTINGS (UPDATE PASSWORD GSHEETS) ---
elif menu == "SECURITY SETTINGS":
    st.title("🔒 SECURITY_VAULT")
    with st.form("p_change"):
        st.write(f"Update Key untuk User: **{user_now}**")
        new_p = st.text_input("NEW ACCESS KEY", type="password")
        if st.form_submit_button("CONFIRM UPDATE"):
            if new_p:
                if update_password_gsheet(user_now, new_p):
                    st.success("Access Key berhasil diperbarui di Cloud (GSheets)!")
                else:
                    st.error("Gagal memperbarui password.")
            else:
                st.warning("Password tidak boleh kosong.")
