import streamlit as st
from datetime import datetime, timedelta, date
import urllib.parse
import re
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

st.set_page_config(
    page_title="Studio Lau Moreira - Agendamento",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
.main { background-color: #faf9f6; }
h1, h2, h3 { color: #4a3b32; font-family: 'Helvetica Neue', sans-serif; }

/* BOTÕES MAIORES E MAIS CONFORTÁVEIS */
.stButton>button { 
    background-color: #d4a373; 
    color: white; 
    border-radius: 10px; 
    border: none; 
    padding: 0.8rem 1.2rem; 
    font-size: 16px; 
    font-weight: bold; 
    width: 100%; 
    box-shadow: 0px 3px 6px rgba(0,0,0,0.1);
}
.stButton>button:hover { background-color: #bc6c25; color: white; }

.btn-gerenciar > button { background-color: #6c757d !important; color: white !important; padding: 0.5rem !important; font-size: 14px !important; }
.btn-gerenciar > button:hover { background-color: #5a6268 !important; }

.card-admin { background-color: #ffffff; border: 1px solid #eae0d0; border-radius: 8px; padding: 14px; margin-bottom: 12px; box-shadow: 0px 2px 4px rgba(0,0,0,0.05); }
.card-admin, .card-admin p, .card-admin span, .card-admin div { color: #3b2f2f !important; }
.badge-alerta { background-color: #ffeeba; color: #856404; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }
.badge-ok { background-color: #d4edda; color: #155724; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }
.badge-pago { background-color: #d4edda; color: #155724; padding: 2px 6px; border-radius: 6px; font-size: 11px; font-weight: bold; }
.badge-pendente { background-color: #f8d7da; color: #721c24; padding: 2px 6px; border-radius: 6px; font-size: 11px; font-weight: bold; }
.niver-hoje { color: #d9534f; font-weight: bold; font-size: 14px; margin-left: 6px; }
.niver-semana { color: #f0ad4e; font-weight: bold; font-size: 14px; margin-left: 6px; }
.niver-passou { color: #5bc0de; font-weight: bold; font-size: 14px; margin-left: 6px; }
.niver-longe { color: #999; font-weight: bold; font-size: 14px; margin-left: 6px; }
div[data-baseweb="calendar"] > div:last-child { display: none !important; }
</style>
""", unsafe_allow_html=True)

hoje = datetime.now()
hoje_date = hoje.date()

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

if 'confirmar_exclusao' not in st.session_state:
    st.session_state.confirmar_exclusao = None

if 'confirmar_pagamento' not in st.session_state:
    st.session_state.confirmar_pagamento = None

if 'confirmar_exclusao_cliente' not in st.session_state:
    st.session_state.confirmar_exclusao_cliente = None

if 'show_manual_success' not in st.session_state:
    st.session_state.show_manual_success = False

if 'open_manual' not in st.session_state:
    st.session_state.open_manual = False

if 'agendamentos_db' not in st.session_state:
    st.session_state.agendamentos_db = []

def sanitizar_texto(texto):
    if not texto: return ""
    return re.sub(r'[<>"\']', '', texto).strip()

def validar_telefone(tel):
    digitos = re.sub(r'\D', '', tel)
    return len(digitos) >= 10, digitos

def status_aniversario(data_str):
    try:
        dia_n, mes_n = map(int, data_str.split('/'))
        bday_este_ano = date(hoje_date.year, mes_n, dia_n)
        dias_para_niver = (bday_este_ano - hoje_date).days
        
        if dias_para_niver == 0:
            return "<span class='niver-hoje'>— 🎉 É HOJE!</span>"
        elif 1 <= dias_para_niver <= 15:
            return f"<span class='niver-semana'>— 🎂 Fará aniversário dia {data_str}</span>"
        elif -15 <= dias_para_niver <= -1:
            return f"<span class='niver-passou'>— 🎈 Fez aniversário dia {data_str}</span>"
        else:
            return f"<span class='niver-longe'>— 🎂 Aniversário: {data_str}</span>"
    except:
        return ""

def adicionar_ao_google_calendar(nome, servico, data_obj, horario_str, duracao_horas):
    try:
        if "google_credentials" not in st.secrets:
            return False 
        
        cred_dict = dict(st.secrets["google_credentials"])
        cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
        
        credentials = service_account.Credentials.from_service_account_info(
            cred_dict, scopes=['https://www.googleapis.com/auth/calendar']
        )
        service = build('calendar', 'v3', credentials=credentials)
        
        hora, minuto = map(int, horario_str.split(":"))
        inicio_dt = datetime.combine(data_obj, datetime.min.time().replace(hour=hora, minute=minuto))
        fim_dt = inicio_dt + timedelta(hours=duracao_horas)
        
        evento = {
            'summary': f"{servico} - {nome}",
            'description': f"Cliente: {nome}\nProcedimento: {servico}\nGerado automaticamente pelo Studio Lau Moreira.",
            'start': {'dateTime': inicio_dt.isoformat(), 'timeZone': 'America/Sao_Paulo'},
            'end': {'dateTime': fim_dt.isoformat(), 'timeZone': 'America/Sao_Paulo'},
        }
        
        # ID DA AGENDA FIXO AQUI
        calendar_id = "studiolaumoreira@gmail.com"
        service.events().insert(calendarId=calendar_id, body=evento).execute()
        return True
    except Exception as e:
        print(f"Erro ao sincronizar com Google Calendar: {e}")
        return False

meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]

lista_datas = []
for i in range(60):
    data_calc = hoje + timedelta(days=i)
    if 1 <= data_calc.weekday() <= 5: 
        dia_str = dias_semana[data_calc.weekday()]
        mes_str = meses[data_calc.month - 1]
        label_data = f"{dia_str}, {data_calc.day:02d} de {mes_str}"
        lista_datas.append({"label": label_data, "data_obj": data_calc.date()})

servicos_info = {
    "Brow Lamination": {"preco": 100.00, "duracao": 2},
    "Design com Henna": {"preco": 55.00, "duracao": 1},
    "Design com Tintura": {"preco": 55.00, "duracao": 1},
    "Design Personalizado": {"preco": 40.00, "duracao": 1}
}

st.sidebar.title("Menu Restrito")
acesso_admin = st.sidebar.text_input("Acesso da Profissional (Senha):", type="password")
if acesso_admin == "@Aj170414":
    st.session_state.admin_logged_in = True

modo_acesso = "🌸 Portal de Agendamento (Cliente)"
if st.session_state.admin_logged_in:
    modo_acesso = st.sidebar.selectbox("Alternar Modo:", ["🌸 Portal de Agendamento (Cliente)", "🔒 Painel da Profissional (Admin)"])
    if st.sidebar.button("🚪 Sair do Painel Admin"):
        st.session_state.admin_logged_in = False
        st.rerun()

# ==========================================
# MODO 1: PORTAL DA CLIENTE
# ==========================================
if modo_acesso == "🌸 Portal de Agendamento (Cliente)":
    st.title("✨ Studio Lau Moreira")
    st.write("Escolha seu procedimento, data e horário de preferência de forma rápida e prática.")

    if 'etapa' not in st.session_state: st.session_state.etapa = 1

    if st.session_state.etapa == 1:
        st.subheader("1. Escolha o Procedimento")
        servico_escolhido = st.radio("Selecione o serviço:", options=list(servicos_info.keys()), format_func=lambda x: f"{x} - R$ {servicos_info[x]['preco']:.2f} ({servicos_info[x]['duracao']}h)")
        st.markdown("---")
        incluir_buco = st.checkbox("Adicionar Epilação de Buço (+ R$ 15,00)")
        
        preco_total = servicos_info[servico_escolhido]["preco"]
        if incluir_buco: preco_total += 15.00
            
        st.info(f"💼 **Serviço:** {servico_escolhido}" + (" + Epilação de Buço" if incluir_buco else ""))
        st.success(f"💰 **Total:** R$ {preco_total:.2f}")
        
        if st.button("Avançar ➡️"):
            st.session_state.servico = servico_escolhido
            st.session_state.buco = incluir_buco
            st.session_state.preco = preco_total
            st.session_state.duracao_servico = servicos_info[servico_escolhido]["duracao"] + (0.5 if incluir_buco else 0)
            st.session_state.etapa = 2
            st.rerun()

    elif st.session_state.etapa == 2:
        st.subheader("2. Escolha a Data")
        opcoes_labels = [d["label"] for d in lista_datas]
        dia_escolhido_label = st.selectbox("Selecione o dia disponível:", options=opcoes_labels)
        data_obj_escolhida = next(d["data_obj"] for d in lista_datas if d["label"] == dia_escolhido_label)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Voltar"): st.session_state.etapa = 1; st.rerun()
        with col2:
            if st.button("Avançar ➡️"):
                st.session_state.dia = dia_escolhido_label
                st.session_state.data_obj = data_obj_escolhida
                st.session_state.etapa = 3
                st.rerun()

    elif st.session_state.etapa == 3:
        st.subheader(f"3. Horários para {st.session_state.dia}")
        horarios_padrao = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00"]
        horarios_possiveis = []
        
        for h in horarios_padrao:
            hora, minuto = map(int, h.split(":"))
            hora_agendamento = datetime.combine(st.session_state.data_obj, datetime.min.time().replace(hour=hora, minute=minuto))
            
            if (hora_agendamento - hoje).total_seconds() > 3600:
                horarios_possiveis.append(h)
        
        if not horarios_possiveis:
            st.error("⚠️ Não há horários disponíveis com no mínimo 1 hora de antecedência para este dia.")
            if st.button("⬅️ Escolher outra data"): st.session_state.etapa = 2; st.rerun()
        else:
            horario_escolhido = st.selectbox("Selecione o horário:", options=horarios_possiveis)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⬅️ Voltar"): st.session_state.etapa = 2; st.rerun()
            with col2:
                if st.button("Avançar ➡️"):
                    st.session_state.horario = horario_escolhido
                    st.session_state.etapa = 4
                    st.rerun()

    elif st.session_state.etapa == 4:
        st.subheader("4. Seus Dados de Contato")
        nome_cliente = st.text_input("Seu Nome Completo (Sugestão: Nome e Sobrenome):")
        whatsapp_cliente = st.text_input("Seu WhatsApp (com DDD, ex: 41999998888):")
        aniversario_cliente = st.text_input("Data de Aniversário:", max_chars=5)
        
        st.markdown("---")
        st.write(f"📋 **Resumo:** {st.session_state.servico} | R$ {st.session_state.preco:.2f} | {st.session_state.dia} às {st.session_state.horario}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Voltar"): st.session_state.etapa = 3; st.rerun()
        with col2:
            if st.button("✅ Confirmar Agendamento"):
                nome_limpo = sanitizar_texto(nome_cliente)
                tel_valido, tel_limpo = validar_telefone(whatsapp_cliente)
                aniv_numeros = re.sub(r'\D', '', aniversario_cliente)

                if len(nome_limpo) < 2:
                    st.error("Preencha o nome corretamente.")
                elif not tel_valido:
                    st.error("WhatsApp inválido. Digite o DDD e o número.")
                elif len(aniv_numeros) != 4:
                    st.error("Digite o dia e o mês do seu aniversário (ex: 15/05 ou 1505).")
                else:
                    aniversario_formatado = f"{aniv_numeros[:2]}/{aniv_numeros[2:]}"
                    servico_completo = st.session_state.servico + (" + Epilação de Buço" if st.session_state.buco else "")
                    
                    novo_agendamento = {
                        "nome": nome_limpo,
                        "whatsapp": tel_limpo,
                        "aniversario": aniversario_formatado,
                        "servico": servico_completo,
                        "valor": st.session_state.preco,
                        "dia": st.session_state.dia,
                        "data_obj": st.session_state.data_obj,
                        "horario": st.session_state.horario,
                        "status": "Agendado",
                        "pagamento": "Pendente"
                    }
                    st.session_state.agendamentos_db.append(novo_agendamento)
                    
                    adicionar_ao_google_calendar(
                        nome_limpo, 
                        servico_completo, 
                        st.session_state.data_obj, 
                        st.session_state.horario, 
                        st.session_state.duracao_servico
                    )
                    
                    st.session_state.nome = nome_limpo
                    st.session_state.whatsapp_raw = tel_limpo
                    st.session_state.aniversario = aniversario_formatado
                    st.session_state.etapa = 5
                    st.rerun()

    elif st.session_state.etapa == 5:
        st.success("🎉 Agendamento realizado com sucesso e sincronizado com o Google Agenda!")
        texto_msg = f"Olá! Novo agendamento:\n- Cliente: {st.session_state.nome}\n- Procedimento: {st.session_state.servico}\n- Data: {st.session_state.dia} às {st.session_state.horario}"
        link_whatsapp = f"https://wa.me/5541995312006?text={urllib.parse.quote(texto_msg)}"
        
        st.markdown(f'<a href="{link_whatsapp}" target="_blank"><button style="background-color: #25d366; color: white; padding: 14px; border-radius: 10px; width: 100%; font-weight: bold; font-size: 16px; border: none;">📲 Enviar no WhatsApp</button></a>', unsafe_allow_html=True)
        if st.button("🔄 Novo Agendamento"):
            for key in list(st.session_state.keys()):
                if key != 'agendamentos_db' and key != 'admin_logged_in': 
                    del st.session_state[key]
            st.rerun()

# ==========================================
# MODO 2: PAINEL ADMIN (OCULTO PARA CLIENTES)
# ==========================================
elif modo_acesso == "🔒 Painel da Profissional (Admin)":
    st.subheader("🔒 Painel de Gestão")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Agenda", "👥 Clientes", "💰 Financeiro", "🕰️ Fichas & Pré-Venda"])
    
    with tab1:
        if st.session_state.show_manual_success:
            st.success("✅ Agendamento manual adicionado e sincronizado com o Google Agenda!")
            st.session_state.show_manual_success = False

        with st.expander("➕ Adicionar Agendamento Manual", expanded=st.session_state.open_manual):
            st.write("Agende clientes que entraram em contato direto pelo WhatsApp:")
            nome_m = st.text_input("Nome da Cliente (Sugestão: Nome e Sobrenome):", key="m_nome")
            wpp_m = st.text_input("WhatsApp (com DDD):", key="m_wpp")
            aniv_m = st.text_input("Data de Aniversário:", max_chars=5, key="m_aniv")
            
            serv_m = st.selectbox("Procedimento:", list(servicos_info.keys()))
            buco_m = st.checkbox("Incluir Epilação de Buço (+ R$ 15,00)")
            
            opcoes_labels_m = [d["label"] for d in lista_datas]
            dia_m_label = st.selectbox("Dia do Atendimento:", options=opcoes_labels_m)
            horario_m = st.selectbox("Horário:", ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00"])
            
            if st.button("✅ Salvar Agendamento Manual"):
                aniv_numeros_m = re.sub(r'\D', '', aniv_m)
                if len(nome_m) < 2 or len(re.sub(r'\D', '', wpp_m)) < 10 or len(aniv_numeros_m) != 4:
                    st.error("Preencha Nome, WhatsApp válido e os 4 números do Aniversário.")
                else:
                    data_obj_m = next(d["data_obj"] for d in lista_datas if d["label"] == dia_m_label)
                    preco_m = servicos_info[serv_m]["preco"] + (15.00 if buco_m else 0)
                    duracao_m = servicos_info[serv_m]["duracao"] + (0.5 if buco_m else 0)
                    servico_completo_m = serv_m + (" + Epilação de Buço" if buco_m else "")
                    aniv_formatado_m = f"{aniv_numeros_m[:2]}/{aniv_numeros_m[2:]}"
                    
                    st.session_state.agendamentos_db.append({
                        "nome": nome_m, "whatsapp": re.sub(r'\D', '', wpp_m), "aniversario": aniv_formatado_m,
                        "servico": servico_completo_m, "valor": preco_m, "dia": dia_m_label,
                        "data_obj": data_obj_m, "horario": horario_m, "status": "Agendado", "pagamento": "Pendente"
                    })
                    
                    adicionar_ao_google_calendar(
                        nome_m, 
                        servico_completo_m, 
                        data_obj_m, 
                        horario_m, 
                        duracao_m
                    )
                    
                    st.session_state.show_manual_success = True
                    st.session_state.open_manual = False
                    for k in ["m_nome", "m_wpp", "m_aniv"]:
                        if k in st.session_state:
                            del st.session_state[k]
                    st.rerun()

        st.write("---")
        st.write("**Lista de Agendamentos (Hoje e Futuros):**")
        
        agendamentos_ordenados = sorted(enumerate(st.session_state.agendamentos_db), key=lambda x: x[1]["data_obj"])
        
        tem_futuro = False
        for original_idx, ag in agendamentos_ordenados:
            if ag["data_obj"] >= hoje_date and ag.get("status", "Agendado") == "Agendado":
                tem_futuro = True
                data_formatada = ag["data_obj"].strftime("%d/%m/%Y")
                alerta_niver = status_aniversario(ag['aniversario'])
                
                st.markdown(f"<div class='card-admin'><b>{ag['nome']}</b> {alerta_niver}<br>📞 {ag['whatsapp']}<br>{ag['servico']}<br>📅 {data_formatada} às {ag['horario']}</div>", unsafe_allow_html=True)
                
                if st.session_state.confirmar_exclusao == original_idx:
                    st.warning(f"O que aconteceu com o agendamento de {ag['nome']}?")
                    col_veio, col_faltou = st.columns(2)
                    
                    if col_veio.button("✔️ Compareceu (Realizado)", key=f"veio_{original_idx}"):
                        st.session_state.confirmar_exclusao = None
                        st.session_state.confirmar_pagamento = original_idx
                        st.rerun()
                        
                    if col_faltou.button("❌ Não Compareceu (Falta)", key=f"falta_{original_idx}"):
                        st.session_state.agendamentos_db[original_idx]["status"] = "Falta"
                        st.session_state.confirmar_exclusao = None
                        st.rerun()
                        
                    if st.button("⬅️ Voltar / Não fazer nada", key=f"voltar_{original_idx}"):
                        st.session_state.confirmar_exclusao = None
                        st.rerun()
                        
                elif st.session_state.confirmar_pagamento == original_idx:
                    st.info(f"Como foi o pagamento do procedimento de {ag['nome']}?")
                    col_pago, col_pendente = st.columns(2)
                    
                    if col_pago.button("💵 Pago", key=f"pago_sim_{original_idx}"):
                        st.session_state.agendamentos_db[original_idx]["status"] = "Realizado"
                        st.session_state.agendamentos_db[original_idx]["pagamento"] = "Pago"
                        st.session_state.confirmar_pagamento = None
                        st.rerun()
                        
                    if col_pendente.button("⏳ Pendente", key=f"pago_nao_{original_idx}"):
                        st.session_state.agendamentos_db[original_idx]["status"] = "Realizado"
                        st.session_state.agendamentos_db[original_idx]["pagamento"] = "Pendente"
                        st.session_state.confirmar_pagamento = None
                        st.rerun()
                        
                    if st.button("⬅️ Voltar / Alterar", key=f"voltar_pag_{original_idx}"):
                        st.session_state.confirmar_pagamento = None
                        st.session_state.confirmar_exclusao = original_idx
                        st.rerun()
                else:
                    st.markdown("<div class='btn-gerenciar'>", unsafe_allow_html=True)
                    if st.button(f"⚙️ Gerenciar Agendamento", key=f"del_{original_idx}"):
                        st.session_state.confirmar_exclusao = original_idx
                        st.rerun()
                    st.markdown("</div><br>", unsafe_allow_html=True)
        
        if not tem_futuro:
            st.info("Nenhum agendamento futuro no momento.")
                
    with tab2:
        st.write("Base de Clientes (Gerenciamento):")
        
        clientes_unicos = {}
        for idx, ag in enumerate(st.session_state.agendamentos_db):
            wpp = ag['whatsapp']
            if wpp not in clientes_unicos:
                clientes_unicos[wpp] = {"nome": ag['nome'], "aniversario": ag['aniversario'], "indices": []}
            clientes_unicos[wpp]["indices"].append(idx)
        
        if not clientes_unicos:
            st.info("Nenhuma cliente cadastrada na base ainda.")
        else:
            for wpp, dados in clientes_unicos.items():
                alerta_niver = status_aniversario(dados['aniversario'])
                
                with st.expander(f"👤 {dados['nome']} — 📞 {wpp}"):
                    st.markdown(f"🎂 **Aniversário:** {dados['aniversario']} {alerta_niver}", unsafe_allow_html=True)
                    st.markdown("---")
                    
                    st.write("✏️ **Editar Dados da Cliente:**")
                    novo_nome = st.text_input("Nome:", value=dados['nome'], key=f"edit_nome_{wpp}")
                    novo_wpp = st.text_input("WhatsApp:", value=wpp, key=f"edit_wpp_{wpp}")
                    novo_aniv = st.text_input("Aniversário (DD/MM):", value=dados['aniversario'], key=f"edit_aniv_{wpp}")
                    
                    if st.button("💾 Salvar Alterações", key=f"salvar_{wpp}"):
                        for idx in dados["indices"]:
                            st.session_state.agendamentos_db[idx]["nome"] = sanitizar_texto(novo_nome)
                            st.session_state.agendamentos_db[idx]["whatsapp"] = re.sub(r'\D', '', novo_wpp)
                            st.session_state.agendamentos_db[idx]["aniversario"] = sanitizar_texto(novo_aniv)
                        st.success("Dados atualizados com sucesso!")
                        st.rerun()
                        
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    if st.session_state.confirmar_exclusao_cliente == wpp:
                        st.warning(f"Tem certeza que deseja excluir permanentemente a cliente {dados['nome']} e todo o seu histórico?")
                        col_s, col_n = st.columns(2)
                        if col_s.button("✔️️ Sim, Excluir", key=f"sim_cli_{wpp}"):
                            st.session_state.agendamentos_db = [ag for ag in st.session_state.agendamentos_db if ag['whatsapp'] != wpp]
                            st.session_state.confirmar_exclusao_cliente = None
                            st.success("Cliente excluída da base de dados.")
                            st.rerun()
                        if col_n.button("✖️ Cancelar", key=f"nao_cli_{wpp}"):
                            st.session_state.confirmar_exclusao_cliente = None
                            st.rerun()
                    else:
                        st.markdown("<div class='btn-gerenciar'>", unsafe_allow_html=True)
                        if st.button(f"🗑️ Excluir Cliente da Base", key=f"del_cli_{wpp}"):
                            st.session_state.confirmar_exclusao_cliente = wpp
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
                
    with tab3:
        st.write("Visão Financeira")
        
        filtro_fin = st.radio("Período de Análise:", ["Esta Semana", "Este Mês", "Todo o Período", "Personalizado"], horizontal=True)
        
        data_inicio, data_fim = None, None
        if filtro_fin == "Personalizado":
            st.write("Selecione o intervalo de datas:")
            datas_selecionadas = st.date_input("Intervalo:", [hoje_date - timedelta(days=90), hoje_date], format="DD/MM/YYYY")
            
            if len(datas_selecionadas) == 2:
                data_inicio, data_fim = datas_selecionadas
            else:
                st.warning("Selecione a data de início e a data de fim.")

        fat_realizado, qtd_realizado = 0, 0
        fat_previsto, qtd_previsto = 0, 0
        
        for ag in st.session_state.agendamentos_db:
            d = ag["data_obj"]
            status_ag = ag.get("status", "Agendado")
            status_pagamento = ag.get("pagamento", "Pendente")
            
            if status_ag == "Falta":
                continue
            
            incluir = False
            if filtro_fin == "Todo o Período":
                incluir = True
            elif filtro_fin == "Este Mês":
                if d.year == hoje_date.year and d.month == hoje_date.month: incluir = True
            elif filtro_fin == "Esta Semana":
                if d.isocalendar()[1] == hoje_date.isocalendar()[1] and d.year == hoje_date.year: incluir = True
            elif filtro_fin == "Personalizado" and data_inicio and data_fim:
                if data_inicio <= d <= data_fim: incluir = True
            
            if incluir:
                if (d <= hoje_date or status_ag == "Realizado") and status_pagamento == "Pago":
                    fat_realizado += ag["valor"]
                    qtd_realizado += 1
                elif status_ag == "Agendado" or (status_ag == "Realizado" and status_pagamento == "Pendente"):
                    if d > hoje_date or status_pagamento == "Pendente":
                        fat_previsto += ag["valor"]
                        qtd_previsto += 1
        
        col_realizado, col_previsto = st.columns(2)
        with col_realizado:
            st.metric(label="✅ Faturamento Realizado (Pago)", value=f"R$ {fat_realizado:.2f}", delta=f"{qtd_realizado} pagos", delta_color="normal")
        with col_previsto:
            st.metric(label="⏳ Previsto / Pendente", value=f"R$ {fat_previsto:.2f}", delta=f"{qtd_previsto} itens", delta_color="off")

    with tab4:
        st.write("Ficha de Clientes (CRM) - Controle de Retoque & Pagamento")
        st.caption("Acompanhe o histórico, o status de pagamento e saiba quem chamar para retoque.")
        
        passados = [ag for ag in st.session_state.agendamentos_db if ag["data_obj"] <= hoje_date or ag.get("status") == "Realizado"]
        
        fichas = {}
        for ag in passados:
            if ag.get("status") == "Falta": continue
            w = ag["whatsapp"]
            if w not in fichas: fichas[w] = {"nome": ag["nome"], "agendamentos": []}
            fichas[w]["agendamentos"].append(ag)
        
        if not fichas:
            st.info("Nenhum histórico de procedimentos realizados no período selecionado.")
        else:
            for w, dados in fichas.items():
                historico_ordenado = sorted(dados["agendamentos"], key=lambda x: x["data_obj"], reverse=True)
                ultimo_ag = historico_ordenado[0]
                dias_passados = (hoje_date - ultimo_ag["data_obj"]).days
                
                tag_dias = f"<span class='badge-alerta'>Há {dias_passados} dias</span>" if dias_passados > 30 else f"<span class='badge-ok'>Há {dias_passados} dias</span>"
                
                with st.expander(f"👤 {dados['nome']} — Última visita: {dias_passados} dias atrás"):
                    st.markdown(f"**Contato:** {w}")
                    st.markdown(f"**Último Serviço:** {ultimo_ag['servico']} ({tag_dias})", unsafe_allow_html=True)
                    st.markdown("---")
                    st.markdown("**Histórico Completo de Atendimentos:**")
                    
                    for item_idx, item in enumerate(historico_ordenado):
                        data_f = item["data_obj"].strftime("%d/%m/%Y")
                        pag_status = item.get("pagamento", "Pendente")
                        badge_pag = f"<span class='badge-pago'>Pago</span>" if pag_status == "Pago" else f"<span class='badge-pendente'>Pendente</span>"
                        
                        st.write(f"- {data_f}: {item['servico']} (R$ {item['valor']:.2f}) | Status: {badge_pag}", unsafe_allow_html=True)
                        
                        if pag_status == "Pendente":
                            if st.button(f"Confirmar Pagamento de {item['servico']} ({data_f})", key=f"conf_pag_{w}_{item_idx}"):
                                for real_ag in st.session_state.agendamentos_db:
                                    if real_ag['whatsapp'] == w and real_ag['data_obj'] == item['data_obj'] and real_ag['servico'] == item['servico']:
                                        real_ag['pagamento'] = "Pago"
                                st.success("Pagamento confirmado com sucesso!")
                                st.rerun()

                    st.markdown("<br>", unsafe_allow_html=True)
                    msg_prevenda = urllib.parse.quote(f"Oi {dados['nome']}! Tudo bem? Vi aqui na ficha que já faz um tempinho desde o seu último {ultimo_ag['servico']}. Vamos agendar seu retorno?")
                    link_wpp = f"https://wa.me/55{w}?text={msg_prevenda}"
                    st.markdown(f'<a href="{link_wpp}" target="_blank"><button style="background-color: #25d366; color: white; padding: 10px; border-radius: 8px; width: 100%; border: none; font-size: 15px; font-weight: bold;">💬 Chamar para Retoque</button></a>', unsafe_allow_html=True)
