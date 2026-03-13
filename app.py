"""
ConPrev — Análise de Restrições  ·  Interface Web (Streamlit)

Substitui a janela Tkinter por uma UI hospedável em nuvem com design
fiel ao Painel CND (navy + amber, Sora + IBM Plex Mono).

Deploy gratuito: https://streamlit.io/cloud
Uso local      : streamlit run app.py
"""
from __future__ import annotations

import hashlib
import io
import os
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Callable
from unittest.mock import MagicMock

import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# 1.  Patch Tkinter ANTES de importar o módulo (servidor headless não tem Tk)
# ─────────────────────────────────────────────────────────────────────────────
for _stub in ("tkinter", "tkinter.filedialog", "tkinter.messagebox"):
    sys.modules.setdefault(_stub, MagicMock())

try:
    from relatorio_restricoes_module import MUNICIPIOS_POR_UF, analisar_restricoes
except Exception as _import_err:
    # Mostra erro apenas depois que a página está configurada
    _IMPORT_ERROR: str | None = str(_import_err)
    MUNICIPIOS_POR_UF = {}
    analisar_restricoes = None  # type: ignore[assignment]
else:
    _IMPORT_ERROR = None

# ─────────────────────────────────────────────────────────────────────────────
# 2.  Page config — DEVE ser o primeiro comando Streamlit
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ConPrev — Análise de Restrições",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# 3.  CSS — Tema ConPrev (espelha o Painel CND)
# ─────────────────────────────────────────────────────────────────────────────
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
    --navy:   #0B1E33;  --navy2:  #112840;  --navy3:  #1c3f60;
    --blue:   #1a6faf;  --sky:    #2d8fd4;
    --amber:  #F29F05;  --amber2: #d78904;
    --red:    #d63b3b;  --green:  #2a9c6b;  --yellow: #e8a020;
    --text:   #e8edf2;  --muted:  #8ba4bc;
    --card:   rgba(255,255,255,0.04);
    --border: rgba(255,255,255,0.08);
}

/* Fundo global */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section[data-testid="stMain"] {
    background: var(--navy) !important;
}
[data-testid="stHeader"] {
    background: var(--navy2) !important;
    border-bottom: 1px solid var(--border);
}

/* Tipografia global */
html, body, .stApp, .stMarkdown, p, span, div, label {
    font-family: 'Sora', sans-serif !important;
    color: var(--text);
}

/* Inputs de texto */
.stTextInput > div > div > input {
    background: rgba(255,255,255,.06) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    font-family: 'Sora', sans-serif !important;
}
.stTextInput > div > div > input[type="password"] {
    font-family: 'IBM Plex Mono', monospace !important;
    letter-spacing: 4px;
    font-size: 18px !important;
}
.stTextInput > div > div > input:focus {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 3px rgba(26,111,175,.2) !important;
}
.stTextInput > label { color: var(--muted) !important; font-size: 12px !important;
    font-weight: 600 !important; text-transform: uppercase; letter-spacing: .8px; }

/* Botão primário (amber) */
.stButton > button[kind="primary"],
button[data-testid="baseButton-primary"] {
    background: var(--amber) !important;
    color: #111 !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 12px 28px !important;
    font-size: 15px !important;
    font-family: 'Sora', sans-serif !important;
    transition: background .2s, transform .1s !important;
}
.stButton > button[kind="primary"]:hover { background: var(--amber2) !important; }
.stButton > button[kind="primary"]:active { transform: scale(.98) !important; }

/* Botão secundário */
.stButton > button:not([kind="primary"]) {
    background: transparent !important;
    border: 1px solid var(--border) !important;
    color: var(--muted) !important;
    border-radius: 8px !important;
    font-family: 'Sora', sans-serif !important;
    transition: border-color .2s, color .2s !important;
}
.stButton > button:not([kind="primary"]):hover {
    border-color: var(--amber) !important;
    color: var(--amber) !important;
}

/* Radio */
.stRadio > div { gap: 16px !important; }
.stRadio > div > label { color: var(--text) !important; font-size: 13px !important; }
.stRadio [data-baseweb="radio"] > div:first-child {
    border-color: var(--border) !important;
    background: transparent !important;
}
.stRadio [data-baseweb="radio"][aria-checked="true"] > div:first-child {
    border-color: var(--amber) !important;
    background: var(--amber) !important;
}

/* Checkboxes */
.stCheckbox > label { color: var(--text) !important; font-size: 13px !important; }
.stCheckbox { margin-bottom: 3px !important; }
[data-baseweb="checkbox"] > div:first-child {
    border-color: var(--border) !important;
    background: transparent !important;
    border-radius: 4px !important;
}
[data-baseweb="checkbox"][aria-checked="true"] > div:first-child {
    background: var(--amber) !important;
    border-color: var(--amber) !important;
}

/* File uploader */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,.03) !important;
    border: 1px dashed var(--border) !important;
    border-radius: 12px !important;
}
[data-testid="stFileUploader"] section { background: transparent !important; }
[data-testid="stFileUploaderDropzone"] { background: transparent !important; }

/* Download button */
.stDownloadButton > button {
    background: rgba(42,156,107,.12) !important;
    color: #3fc98a !important;
    border: 1px solid rgba(42,156,107,.28) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-family: 'Sora', sans-serif !important;
    transition: background .2s !important;
}
.stDownloadButton > button:hover { background: rgba(42,156,107,.22) !important; }

/* Alertas */
.stAlert { border-radius: 10px !important; }
[data-testid="stNotification"] { background: var(--navy2) !important; border-radius: 10px !important; }

/* Log / code block */
.stCodeBlock pre, pre {
    background: #0d1e30 !important;
    color: #3fc98a !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 12px !important;
    border-radius: 8px !important;
    border: 1px solid var(--border) !important;
}

/* Spinner */
[data-testid="stSpinner"] > div { color: var(--amber) !important; }

/* Divisor */
hr { border-color: var(--border) !important; margin: 16px 0 !important; }

/* Esconde chrome desnecessário */
#MainMenu, footer,
[data-testid="stDecoration"],
[data-testid="stToolbar"] { display: none !important; }

/* Scrollbar discreta */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--navy); }
::-webkit-scrollbar-thumb { background: var(--navy3); border-radius: 3px; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 4.  Constantes
# ─────────────────────────────────────────────────────────────────────────────
# SHA-256 de "conprev2026"  — troque pelo hash da nova senha se necessário
_PWD_HASH = "d8def52178c00ca7dd0e4a0a144cdc84d3e0c1ce48a61aacafa0ae0eccc3cb8b"
_REF_DATE = "12/03/2026"
_UFS: tuple[str, ...] = ("GO", "TO", "MS")


def _sha256(text: str) -> str:
    """SHA-256 hex digest de uma string UTF-8."""
    return hashlib.sha256(text.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# 5.  Estado da sessão
# ─────────────────────────────────────────────────────────────────────────────
ss = st.session_state
ss.setdefault("authenticated", False)
ss.setdefault("result_zip_bytes", None)
ss.setdefault("result_file_count", 0)
ss.setdefault("analysis_done", False)


# ─────────────────────────────────────────────────────────────────────────────
# 6.  Componentes de UI reutilizáveis
# ─────────────────────────────────────────────────────────────────────────────

def _card(title: str, icon: str = "") -> None:
    """Renderiza um cabeçalho de card estilizado."""
    st.markdown(
        f"""<div style="
            background:rgba(255,255,255,.04);
            border:1px solid rgba(255,255,255,.08);
            border-radius:14px 14px 0 0;
            padding:14px 20px;
            margin-bottom:0;
        ">
            <span style="font-size:11px;font-weight:600;color:#8ba4bc;
                         text-transform:uppercase;letter-spacing:.8px">
                {icon} {title}
            </span>
        </div>""",
        unsafe_allow_html=True,
    )


def _badge_pill(text: str, color: str) -> str:
    """Retorna HTML de um badge/pill colorido."""
    return (
        f'<span style="display:inline-flex;align-items:center;gap:5px;'
        f'font-family:IBM Plex Mono,monospace;font-size:12px;font-weight:600;'
        f'padding:4px 10px;border-radius:20px;'
        f'background:rgba({color},.15);color:rgb({color})">'
        f'{text}</span>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7.  Tela de Login
# ─────────────────────────────────────────────────────────────────────────────

def render_login() -> None:
    """Renderiza o formulário de login centralizado."""
    _, col, _ = st.columns([1.3, 1, 1.3])
    with col:
        st.markdown(
            """
            <div style="text-align:center;margin:60px 0 28px">
                <div style="
                    width:56px;height:56px;
                    background:linear-gradient(135deg,#1a6faf,#2d8fd4);
                    border-radius:14px;
                    display:inline-flex;align-items:center;justify-content:center;
                    font-size:26px;
                    box-shadow:0 8px 24px rgba(26,111,175,.4);
                    margin-bottom:12px
                ">🛡️</div>
                <h2 style="font-size:22px;font-weight:700;color:#e8edf2;margin:0 0 4px">
                    ConPrev
                </h2>
                <p style="font-size:11px;color:#8ba4bc;letter-spacing:1px;
                           text-transform:uppercase;margin:0">
                    Análise de Restrições &middot; Acesso Restrito
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        pwd = st.text_input(
            "Senha de acesso",
            type="password",
            placeholder="••••••••",
        )

        if st.button("Entrar", type="primary", use_container_width=True):
            if _sha256(pwd) == _PWD_HASH:
                ss.authenticated = True
                st.rerun()
            else:
                st.error("⚠️ Senha incorreta. Tente novamente.")

        st.markdown(
            '<p style="text-align:center;font-size:11px;color:#8ba4bc;margin-top:20px">'
            "🔒 Dados restritos &middot; Conprev Assessoria</p>",
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 8.  Header da aplicação
# ─────────────────────────────────────────────────────────────────────────────

def render_header() -> None:
    """Renderiza o cabeçalho com branding e botão de logout."""
    left, right = st.columns([4, 1])
    with left:
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:12px;padding:8px 0 4px">
                <div style="
                    width:38px;height:38px;
                    background:linear-gradient(135deg,#1a6faf,#2d8fd4);
                    border-radius:9px;
                    display:flex;align-items:center;justify-content:center;
                    font-size:18px;flex-shrink:0
                ">🛡️</div>
                <div>
                    <div style="font-size:17px;font-weight:700;color:#e8edf2;line-height:1.2">
                        ConPrev &mdash; Análise de Restrições
                    </div>
                    <div style="font-size:11px;color:#8ba4bc">
                        Relatórios de Restrições (RFB/PGFN) &middot; GO / MS / TO
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f'<div style="text-align:right;padding-top:8px">'
            f'<span style="font-family:\'IBM Plex Mono\',monospace;font-size:11px;'
            f'color:#8ba4bc;background:rgba(255,255,255,.05);'
            f'border:1px solid rgba(255,255,255,.08);'
            f'border-radius:6px;padding:4px 10px">Ref.: {_REF_DATE}</span></div>',
            unsafe_allow_html=True,
        )
        if st.button("↩ Sair", key="logout_btn"):
            ss.authenticated = False
            ss.result_zip_bytes = None
            ss.analysis_done = False
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# 9.  Lógica de análise (bridge para analisar_restricoes)
# ─────────────────────────────────────────────────────────────────────────────

def _save_uploads_to_tmpdir(uploaded_files: list) -> Path:
    """
    Salva UploadedFile objects em diretório temporário.
    Suporta .pdf direto e .zip contendo PDFs (extrai automaticamente).

    Complexidade: O(n * tamanho_arquivo) — leitura sequencial dos uploads.
    """
    tmp = Path(tempfile.mkdtemp())
    for uf in uploaded_files:
        data = uf.read()
        if uf.name.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                for member in zf.namelist():
                    if member.lower().endswith(".pdf"):
                        zf.extract(member, tmp)
        else:
            (tmp / uf.name).write_bytes(data)
    return tmp


def _zip_directory_to_bytes(directory: Path) -> bytes:
    """
    Cria um ZIP em memória de todos os arquivos em `directory`.
    Usa ZIP_DEFLATED para compressão razoável de PDFs/TXTs.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(directory.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(directory))
    return buf.getvalue()


def run_analysis(
    uploaded_files: list,
    municipios: list[str],
    log_placeholder,
    logo_bytes: bytes | None = None,
) -> tuple[bytes, int] | None:
    """
    Orquestra todo o fluxo de análise de restrições:

    1. Persiste uploads em tmpdir efêmero
    2. Salva logo (se fornecida) e expõe via env var
    3. Chama analisar_restricoes com callback de log em tempo real
    4. Compacta saídas em ZIP em memória
    5. Limpa diretórios temporários no bloco finally

    Returns:
        (zip_bytes, file_count) em caso de sucesso, None em caso de erro.
    """
    if analisar_restricoes is None:
        st.error(f"❌ Módulo não carregado: {_IMPORT_ERROR}")
        return None

    log_lines: list[str] = []

    def log_cb(msg: str) -> None:
        log_lines.append(str(msg))
        # Atualiza o placeholder a cada log — renderização em tempo real
        log_placeholder.code("\n".join(log_lines), language=None)

    base_dir: Path | None = None
    out_root: Path | None = None
    logo_tmp: Path | None = None

    try:
        # Configura logo antes de chamar o módulo
        if logo_bytes:
            logo_tmp = Path(tempfile.mkdtemp()) / "logo_conprev.png"
            logo_tmp.write_bytes(logo_bytes)
            os.environ["CONPREV_LOGO"] = str(logo_tmp)
        else:
            os.environ.pop("CONPREV_LOGO", None)

        base_dir = _save_uploads_to_tmpdir(uploaded_files)
        out_root = Path(tempfile.mkdtemp())

        out_dir, *_ = analisar_restricoes(
            base_dir=base_dir,
            municipios_escolhidos=municipios,
            incluir_subpastas=True,
            out_root=out_root,
            log_cb=log_cb,
        )

        file_count = sum(1 for p in out_dir.rglob("*") if p.is_file())
        zip_bytes = _zip_directory_to_bytes(out_dir)
        log_cb(f"\n✅ Concluído — {file_count} arquivo(s) gerado(s).")
        return zip_bytes, file_count

    except RuntimeError as exc:
        st.error(f"❌ {exc}")
        log_cb(f"\n❌ Erro: {exc}")
        return None
    except Exception as exc:
        st.error(f"❌ Erro inesperado: {exc}")
        log_cb(f"\n❌ Erro inesperado: {exc}")
        return None
    finally:
        for d in (base_dir, out_root, logo_tmp.parent if logo_tmp else None):
            if d and d.is_dir():
                shutil.rmtree(d, ignore_errors=True)


# ─────────────────────────────────────────────────────────────────────────────
# 10.  Aplicação principal
# ─────────────────────────────────────────────────────────────────────────────

def render_app() -> None:
    """Renderiza a interface principal após autenticação."""

    # ── Erro de importação ────────────────────────────────────────────────────
    if _IMPORT_ERROR:
        st.error(
            f"❌ `relatorio_restricoes_module.py` não encontrado ou com erro:\n\n"
            f"`{_IMPORT_ERROR}`\n\n"
            "Certifique-se de que o arquivo está na **mesma pasta** que `app.py`."
        )
        return

    render_header()
    st.divider()

    # ── Layout de duas colunas ────────────────────────────────────────────────
    col_left, col_right = st.columns([1.1, 1], gap="large")

    # ── Painel esquerdo: seleção de municípios ────────────────────────────────
    with col_left:
        _card("Seleção de Municípios", "🗂")

        with st.container():
            uf = st.radio(
                "Filtrar por UF",
                _UFS,
                horizontal=True,
                key="uf_radio",
            )

        muns: list[str] = MUNICIPIOS_POR_UF.get(uf, [])
        sel_key = f"mun_sel_{uf}"
        if sel_key not in ss:
            ss[sel_key] = {m: False for m in muns}

        # Botões de seleção rápida
        b1, b2, _ = st.columns([1, 1, 2])
        with b1:
            if st.button("✅ Todos", key=f"all_{uf}", use_container_width=True):
                ss[sel_key] = {m: True for m in muns}
                st.rerun()
        with b2:
            if st.button("✗ Limpar", key=f"clr_{uf}", use_container_width=True):
                ss[sel_key] = {m: False for m in muns}
                st.rerun()

        # Grade de checkboxes (3 colunas — responsivo no mobile)
        grid = st.columns(3)
        for i, m in enumerate(muns):
            with grid[i % 3]:
                checked = st.checkbox(
                    m,
                    value=ss[sel_key].get(m, False),
                    key=f"cb_{uf}_{m}",
                )
                ss[sel_key][m] = checked

        # Contador de selecionados
        n_sel = sum(ss[sel_key].values())
        st.markdown(
            f'<p style="font-size:12px;color:#8ba4bc;margin-top:8px">'
            f"<b style='color:#F29F05'>{n_sel}</b> de {len(muns)} municípios selecionados</p>",
            unsafe_allow_html=True,
        )

    # ── Painel direito: upload de arquivos ────────────────────────────────────
    with col_right:
        _card("Upload dos Relatórios de Restrições", "📤")

        uploaded = st.file_uploader(
            "PDFs ou ZIP com os relatórios",
            type=["pdf", "zip"],
            accept_multiple_files=True,
            help=(
                "Selecione os PDFs de relatório de restrições (RFB/PGFN). "
                "Você também pode compactar todos em um .zip e fazer o upload de uma vez."
            ),
            label_visibility="collapsed",
        )

        if uploaded:
            n_pdf = sum(1 for f in uploaded if f.name.lower().endswith(".pdf"))
            n_zip = sum(1 for f in uploaded if f.name.lower().endswith(".zip"))
            parts = []
            if n_pdf:
                parts.append(f"**{n_pdf}** PDF(s)")
            if n_zip:
                parts.append(f"**{n_zip}** ZIP(s)")
            st.success(f"📎 Recebido: {', '.join(parts)}")

        st.markdown("---")

        _card("Logo para os PDFs gerados (opcional)", "🖼")
        logo_file = st.file_uploader(
            "logo_conprev.png",
            type=["png"],
            key="logo_upload",
            label_visibility="collapsed",
            help="Se fornecida, aparece no cabeçalho dos PDFs gerados.",
        )
        if logo_file:
            st.success("✓ Logo carregada")

    # ── Botão de análise ──────────────────────────────────────────────────────
    st.divider()

    selected_muns = [
        m for m in MUNICIPIOS_POR_UF.get(ss.get("uf_radio", "GO"), [])
        if ss.get(f"mun_sel_{ss.get('uf_radio','GO')}", {}).get(m, False)
    ]
    n_upl = len(uploaded) if uploaded else 0

    btn_label = (
        f"🔍 Analisar — {len(selected_muns)} município(s) · {n_upl} arquivo(s)"
        if selected_muns and n_upl
        else "🔍 Analisar Restrições"
    )

    can_run = bool(selected_muns and n_upl)

    if st.button(btn_label, type="primary", use_container_width=True, disabled=not can_run):
        ss.result_zip_bytes = None
        ss.analysis_done = False

        logo_bytes: bytes | None = logo_file.read() if logo_file else None

        log_ph = st.empty()
        with st.spinner("Processando PDFs…"):
            result = run_analysis(uploaded, selected_muns, log_ph, logo_bytes)

        if result:
            ss.result_zip_bytes, ss.result_file_count = result
            ss.analysis_done = True
            st.rerun()

    if not can_run and not ss.analysis_done:
        if not n_upl:
            st.caption("💡 Faça upload dos PDFs de restrição para habilitar a análise.")
        elif not selected_muns:
            st.caption("💡 Selecione ao menos um município para habilitar a análise.")

    # ── Área de resultado / download ──────────────────────────────────────────
    if ss.analysis_done and ss.result_zip_bytes:
        st.markdown(
            """
            <div style="
                background:rgba(42,156,107,.1);
                border:1px solid rgba(42,156,107,.22);
                border-radius:12px;
                padding:20px 22px;
                margin-top:8px
            ">
                <div style="font-weight:700;color:#3fc98a;font-size:15px;margin-bottom:8px">
                    ✅ Análise concluída com sucesso!
                </div>
                <div style="font-size:13px;color:#8ba4bc">
                    Os arquivos PDF e TXT foram gerados e estão prontos para download.
                    O ZIP inclui relatórios individuais por município e o arquivo unificado.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        ts = time.strftime("%Y-%m-%d_%Hh%M")
        st.download_button(
            label=(
                f"⬇️  Baixar todos os arquivos  "
                f"({ss.result_file_count} arquivo(s) — ZIP)"
            ),
            data=ss.result_zip_bytes,
            file_name=f"ConPrev_Restricoes_{ts}.zip",
            mime="application/zip",
            use_container_width=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 11.  Entry point
# ─────────────────────────────────────────────────────────────────────────────
if not ss.authenticated:
    render_login()
else:
    render_app()
