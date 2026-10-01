"""Create the first restaurant and its owner login on an empty database.

Meant for a fresh deploy (for example on Render) where there is no shell to
create users by hand. It reads the details from environment variables, so no
password ever lives in the repo:

    BOOTSTRAP_OWNER_USERNAME   e.g. owner
    BOOTSTRAP_OWNER_PASSWORD   the password you choose (8+ characters)
    BOOTSTRAP_RESTAURANT_NAME  defaults to "Oi Ramen"
    BOOTSTRAP_OUTLET_NAME      defaults to "Main Outlet"
    BOOTSTRAP_TENANT_TYPE      fine_dining | franchise | cafe (default fine_dining)

Safe to run on every start: it does nothing if the variables are unset or the
username already exists, and it never changes an existing password. After the
first successful start you can delete BOOTSTRAP_OWNER_PASSWORD.
"""
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from setup.models import KitchenStation, PaymentConfig
from tenants.models import Outlet, Tenant


class Command(BaseCommand):
    help = "Create the first restaurant + owner from BOOTSTRAP_* environment variables (idempotent)."

    def handle(self, *args, **options):
        username = os.getenv("BOOTSTRAP_OWNER_USERNAME", "").strip()
        password = os.getenv("BOOTSTRAP_OWNER_PASSWORD", "")
        if not username or not password:
            self.stdout.write("bootstrap_owner: BOOTSTRAP_OWNER_* not set, nothing to do.")
            return
        if len(password) < 8:
            self.stderr.write("bootstrap_owner: BOOTSTRAP_OWNER_PASSWORD must be at least 8 characters; skipped.")
            return
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"bootstrap_owner: user '{username}' already exists, nothing to do.")
            return

        name = os.getenv("BOOTSTRAP_RESTAURANT_NAME", "Oi Ramen").strip() or "Oi Ramen"
        outlet_name = os.getenv("BOOTSTRAP_OUTLET_NAME", "Main Outlet").strip() or "Main Outlet"
        tenant_type = os.getenv("BOOTSTRAP_TENANT_TYPE", "fine_dining").strip() or "fine_dining"

        with transaction.atomic():
            tenant = Tenant.objects.create(name=name, tenant_type=tenant_type)
            outlet = Outlet.objects.create(tenant=tenant, name=outlet_name)
            User.objects.create_user(
                username=username, password=password,
                tenant=tenant, outlet=outlet, role="owner",
            )
            KitchenStation.objects.create(tenant=tenant, outlet=outlet, name="Counter", is_default=True)
            PaymentConfig.for_outlet(outlet, tenant)

        self.stdout.write(self.style.SUCCESS(
            f"bootstrap_owner: created '{name}' with owner '{username}'."
        ))
