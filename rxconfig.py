import reflex as rx

config = rx.Config(
    app_name="consultar_registro_db",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
)