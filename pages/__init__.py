"""Page Object Model layer for the WorkFlow Pro automation framework."""

from pages.base_page import BasePage
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage
from pages.projects_page import ProjectsPage

__all__ = ["BasePage", "LoginPage", "DashboardPage", "ProjectsPage"]
