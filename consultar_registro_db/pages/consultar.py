import reflex as rx

def consultar_page() -> rx.Component:
    """Render the consultar page."""
    return rx.container(
        rx.color_mode.button(position="top-right"),
        rx.vstack(
            rx.heading("Consultar Registro", size="9"),
            rx.text("Esta es la página para consultar registros."),
            spacing="5",
            justify="center",
            min_height="85vh",
        ),
    )