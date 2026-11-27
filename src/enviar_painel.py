import os
import asyncio
import smtplib
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path
from playwright.async_api import async_playwright

async def capturar_painel():
    url = os.environ["DASHBOARD_URL"]

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": 1440, "height": 1100},
            device_scale_factor=2
        )
        await page.goto(url, wait_until="networkidle", timeout=120_000)
        quadro = page.locator("#quadro_resumo")
        await quadro.wait_for(state="visible", timeout=60_000)

        # Aguarda os gráficos (incluindo Plotly) terminarem de desenhar.
        await page.wait_for_timeout(4000)
        imagem = await quadro.screenshot(type="png")
        html = await quadro.evaluate("(el) => el.innerHTML")
        await browser.close()

    return imagem, html

def enviar_email(imagem, html):
    destinatario = os.environ["EMAIL_TO"]
    remetente = os.environ.get("EMAIL_FROM", os.environ["SMTP_USER"])
    host = os.environ["SMTP_HOST"]
    porta = int(os.environ.get("SMTP_PORT", "587"))
    usuario = os.environ["SMTP_USER"]
    senha = os.environ["SMTP_PASSWORD"]

    msg = EmailMessage()
    msg["Subject"] = "Painel de indicadores econômicos — atualização semanal"
    msg["From"] = remetente
    msg["To"] = destinatario
    msg["Date"] = formatdate(localtime=True)

    msg.set_content(
        "Segue em anexo/abaixo a captura atualizada do quadro de resumo "
        "dos indicadores econômicos."
    )

    # A imagem preserva a aparência do painel e dos gráficos no e-mail.
    msg.add_alternative(
        """\
        <html>
          <body style="font-family:Arial,sans-serif;color:#222">
            <h2>Painel de indicadores econômicos</h2>
            <p>Atualização semanal do quadro de resumo:</p>
            <img src="cid:quadro_resumo" alt="Quadro resumo"
                 style="display:block;width:100%;max-width:1400px;height:auto">
            <p style="font-size:12px;color:#666">
              Captura automática da seção #quadro_resumo do painel.
            </p>
          </body>
        </html>
        """,
        subtype="html"
    )
    html_part = msg.get_payload()[-1]
    html_part.add_related(
        imagem,
        maintype="image",
        subtype="png",
        cid="<quadro_resumo>",
        filename="quadro_resumo.png"
    )

    with smtplib.SMTP(host, porta) as servidor:
        servidor.ehlo()
        servidor.starttls()
        servidor.ehlo()
        servidor.login(usuario, senha)
        servidor.send_message(msg)

async def main():
    imagem, html = await capturar_painel()
    # Também salva o HTML capturado como artefato/log local do job.
    Path("quadro_resumo.html").write_text(html, encoding="utf-8")
    enviar_email(imagem, html)
    print("E-mail enviado com sucesso.")

if __name__ == "__main__":
    asyncio.run(main())
