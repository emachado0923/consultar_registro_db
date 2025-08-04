import reflex as rx

class User(rx.Model, table=True):
    username: str
    email: str

class QueryState(rx.State):
    documento: str = ""

    @rx.event
    def update_documento(self, new_documento: str):
        self.documento = new_documento

    @rx.event
    def query_document(self):
        with rx.session() as session:
            self.users = session.exec(
                User.select().where(
                    User.username.contains(self.name)
                )
            ).all()
        


def consultar_page() -> rx.Component:
    """Render the consultar page."""
    return rx.container(
        rx.color_mode.button(position="top-right"),
        rx.vstack(
            rx.heading("Consultar Registro", size="9"),
            rx.text("Esta es la página para consultar registros."),
                rx.heading("Ingrese el documento a consultar", size="6"),
                rx.input(
                    default_value=QueryState.documento,
                    on_blur=QueryState.update_documento,
                    placeholder="Documento",
                ),
            
            rx.button("Ingresar", on_click=QueryState.query_document),
            spacing="5",
            justify="center",
            min_height="85vh",
        ),
    )