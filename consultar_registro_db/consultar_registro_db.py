"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx

from rxconfig import config
from . import pages


class State(rx.State):
    """The app state."""

class LoginState(rx.State):
    user: str = ""
    password: str = ""

    @rx.event
    def update_user(self, new_user: str):
        self.user = new_user

    @rx.event
    def update_password(self, new_password: str):
        self.password = new_password


def index() -> rx.Component:
    # Welcome Page (Index)
    return rx.container(
        rx.color_mode.button(position="top-right"),
        rx.vstack(
            rx.heading("Bienvenido a sistema Sapiencia!", size="9"),
            rx.vstack(
                rx.heading("Ingrese usuario y contraseña", size="6"),
                rx.input(
                    default_value=LoginState.user,
                    on_blur=LoginState.update_user,
                    placeholder="Usuario",
                ),
                rx.input(
                    default_value=LoginState.password,
                    on_blur=LoginState.update_password,
                    placeholder="Contraseña",
                    type="password",  # Set input type to password
                ),
                rx.link(
                    rx.button("Ingresar"),
                    href="/consultar",
                    is_external=True,
                ),
            ),
            spacing="5",
            justify="center",
            min_height="85vh",
        ),
    )


app = rx.App()
app.add_page(index)
app.add_page(pages.consultar_page, route="/consultar")
