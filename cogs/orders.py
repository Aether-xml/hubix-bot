import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
from typing import Optional
import io

from utils.database import (
    get_shop_settings, create_shop_settings, update_shop_setting,
    increment_order_counter, add_product, get_products, get_product_by_id,
    update_product, delete_product, toggle_product_stock, get_product_categories,
    decrement_stock, create_order, get_order_by_id, get_order_by_channel,
    get_order_by_number, get_user_orders, get_all_orders, update_order_status,
    update_order_field, get_order_stats, add_review, get_reviews,
    get_average_rating, get_customer_profile, update_customer_profile,
    blacklist_customer, unblacklist_customer, is_customer_blacklisted,
    update_review_message_id, delete_review, get_review_by_id, get_review_count,
    get_last_staff_request, save_staff_request
)
from config import (
    EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR,
    PANEL_COLOR, ORDER_COLOR, PRODUCT_COLOR, DELIVERED_COLOR,
    get_plan_limits
)
from utils.database import get_guild_plan


# ═══════════════════════════════════════════════════════════════
#  PRODUCT SHOP PANEL (Persistent — survives restart)
# ═══════════════════════════════════════════════════════════════

class ShopView(discord.ui.View):
    """The persistent shop panel view with category dropdown."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Order Now",
        style=discord.ButtonStyle.success,
        custom_id="nexify:shop:order",
        emoji="🛒"
    )
    async def order_button(self, interaction: discord.Interaction, button):
        # Plan check
        plan = await get_guild_plan(interaction.guild.id)
        limits = get_plan_limits(plan)
        if not limits.get("shop_enabled"):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="🔒 Feature Locked",
                    description="**Shop/Orders** requires **💎 Basic** plan or higher.\nContact the bot owner to upgrade!",
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )

        settings = await get_shop_settings(interaction.guild.id)
        if not settings or not settings.get("enabled"):
            return await interaction.response.send_message("❌ Shop is not enabled.", ephemeral=True)

        # Check blacklist
        if await is_customer_blacklisted(interaction.guild.id, interaction.user.id):
            return await interaction.response.send_message(
                "❌ You are **blacklisted** from ordering. Contact staff if you think this is a mistake.",
                ephemeral=True
            )

        # Check pending orders
        pending = await get_user_orders(interaction.guild.id, interaction.user.id, "pending")
        processing = await get_user_orders(interaction.guild.id, interaction.user.id, "processing")
        if len(pending) + len(processing) >= 3:
            return await interaction.response.send_message(
                "❌ You have too many active orders. Please wait for your current orders to be completed.",
                ephemeral=True
            )

        products = await get_products(interaction.guild.id)
        in_stock = [p for p in products if p["in_stock"]]

        if not in_stock:
            return await interaction.response.send_message(
                "❌ No products are currently in stock.", ephemeral=True
            )

        view = ProductSelectView(in_stock, settings)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🛒 Select a Product",
                description="Choose the product you'd like to order:",
                color=ORDER_COLOR
            ),
            view=view,
            ephemeral=True
        )

    @discord.ui.button(
        label="My Orders",
        style=discord.ButtonStyle.primary,
        custom_id="nexify:shop:myorders",
        emoji="📦"
    )
    async def my_orders_button(self, interaction: discord.Interaction, button):
        orders = await get_user_orders(interaction.guild.id, interaction.user.id)

        if not orders:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="📦 Your Orders",
                    description="*You haven't placed any orders yet.*",
                    color=WARNING_COLOR
                ),
                ephemeral=True
            )

        status_emoji = {
            "pending": "🟡", "processing": "🔵",
            "delivered": "🟢", "cancelled": "🔴", "refunded": "🟠"
        }

        desc = ""
        for o in orders[:15]:
            se = status_emoji.get(o["status"], "⚪")
            desc += (
                f"{se} `#{o['order_number']:04d}` — **{o['product_name']}** "
                f"| `${o['price']:.2f}` | {o['status'].title()}\n"
            )

        embed = discord.Embed(
            title=f"📦 Your Orders ({len(orders)})",
            description=desc,
            color=ORDER_COLOR
        )

        profile = await get_customer_profile(interaction.guild.id, interaction.user.id)
        if profile:
            embed.add_field(name="💰 Total Spent", value=f"`${profile['total_spent']:.2f}`", inline=True)
            embed.add_field(name="✅ Completed", value=f"`{profile['completed_orders']}`", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="Reviews",
        style=discord.ButtonStyle.secondary,
        custom_id="nexify:shop:reviews",
        emoji="⭐"
    )
    async def reviews_button(self, interaction: discord.Interaction, button):
        plan = await get_guild_plan(interaction.guild.id)
        limits = get_plan_limits(plan)
        if not limits.get("reviews_enabled"):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="🔒 Feature Locked",
                    description="**Reviews** requires **⭐ Premium** plan or higher.\nContact the bot owner to upgrade!",
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )
        reviews = await get_reviews(interaction.guild.id, 10)
        rating_data = await get_average_rating(interaction.guild.id)

        stars = "⭐" * round(rating_data["average"]) if rating_data["average"] else "No ratings yet"

        embed = discord.Embed(
            title="⭐ Customer Reviews",
            description=f"**Average Rating:** {stars} ({rating_data['average']}/5 from {rating_data['count']} reviews)",
            color=ORDER_COLOR
        )

        if reviews:
            for r in reviews[:10]:
                star_text = "⭐" * r["rating"] + "☆" * (5 - r["rating"])
                embed.add_field(
                    name=f"{star_text} — Order #{r['order_number']:04d}",
                    value=f"<@{r['user_id']}>: {r['comment'] or '*No comment*'}\n`{r['product_name']}`",
                    inline=False
                )
        else:
            embed.add_field(name="​", value="*No reviews yet.*", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


# ═══════════════════════════════════════════════════════════════
#  PRODUCT SELECT
# ═══════════════════════════════════════════════════════════════

class ProductSelectView(discord.ui.View):
    def __init__(self, products, settings):
        super().__init__(timeout=120)
        self.settings = settings
        options = []
        for p in products[:25]:
            stock_text = f" (Stock: {p['stock_count']})" if p.get("stock_count") is not None else ""
            reseller = f" | Reseller: ${p['reseller_price']:.2f}" if p.get("reseller_price") else ""
            options.append(discord.SelectOption(
                label=f"{p['name']} — ${p['price']:.2f}",
                value=str(p["id"]),
                emoji=p.get("emoji", "🛒"),
                description=f"{p.get('delivery_time', '5M-2H')}{stock_text}{reseller}"[:100]
            ))

        select = discord.ui.Select(
            placeholder="Select a product...",
            options=options
        )
        select.callback = self.product_selected
        self.add_item(select)

    async def product_selected(self, interaction: discord.Interaction):
        product_id = int(interaction.data["values"][0])
        product = await get_product_by_id(product_id)

        if not product or not product["in_stock"]:
            return await interaction.response.send_message("❌ Product is out of stock!", ephemeral=True)

        # Show product detail + confirm
        embed = discord.Embed(
            title=f"{product['emoji']} {product['name']}",
            description=product.get("description", ""),
            color=PRODUCT_COLOR
        )
        embed.add_field(name="💰 Price", value=f"`${product['price']:.2f}`", inline=True)
        if product.get("reseller_price"):
            embed.add_field(name="🏷️ Reseller Price", value=f"`${product['reseller_price']:.2f}`", inline=True)
        embed.add_field(name="⏱️ Delivery Time", value=f"`{product.get('delivery_time', '5M-2H')}`", inline=True)

        if product.get("stock_count") is not None:
            embed.add_field(name="📦 Stock", value=f"`{product['stock_count']}`", inline=True)

        payment = self.settings.get("payment_methods", "LTC, PayPal")
        embed.add_field(name="💳 Payment Methods", value=f"`{payment}`", inline=False)

        if product.get("image_url"):
            embed.set_image(url=product["image_url"])

        embed.set_footer(text="Click 'Confirm Order' to proceed")

        view = ConfirmOrderView(product, self.settings)
        await interaction.response.edit_message(embed=embed, view=view)


# ═══════════════════════════════════════════════════════════════
#  ORDER CONFIRM + PAYMENT METHOD
# ═══════════════════════════════════════════════════════════════

class ConfirmOrderView(discord.ui.View):
    def __init__(self, product, settings):
        super().__init__(timeout=120)
        self.product = product
        self.settings = settings

        # Payment method select - parse format: emoji Label; (description)
        import re
        raw_methods = settings.get("payment_methods", "")
        options = []
        for line in raw_methods.split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split(";", 1)
            label_part = parts[0].strip()
            desc = parts[1].strip().strip("()") if len(parts) > 1 else None

            # Try to extract custom emoji from label
            emoji_obj = None
            clean_label = label_part

            # Check for custom discord emoji <:name:id> or <a:name:id>
            emoji_match = re.match(r'<(a)?:(\w+):(\d+)>\s*(.*)', label_part)
            if emoji_match:
                animated = bool(emoji_match.group(1))
                emoji_name = emoji_match.group(2)
                emoji_id = int(emoji_match.group(3))
                clean_label = emoji_match.group(4).strip()
                try:
                    emoji_obj = discord.PartialEmoji(name=emoji_name, id=emoji_id, animated=animated)
                except:
                    emoji_obj = None
            else:
                # Check for unicode emoji at start (multi-byte safe)
                import unicodedata
                first_char = label_part[0] if label_part else ""
                try:
                    if first_char and unicodedata.category(first_char).startswith(("So", "Sk")):
                        emoji_obj = first_char
                        clean_label = label_part[1:].strip()
                except:
                    pass

            if not clean_label:
                continue

            opt = discord.SelectOption(
                label=clean_label[:100],
                value=clean_label[:100],
            )
            if desc:
                opt.description = desc[:100]
            if emoji_obj:
                try:
                    opt.emoji = emoji_obj
                except:
                    pass  # Skip invalid emoji silently
            options.append(opt)

        # Fallback if no valid options parsed
        if not options:
            fallback = [m.strip() for m in raw_methods.split(",") if m.strip()]
            if not fallback:
                fallback = ["LTC", "PayPal"]
            for m in fallback:
                options.append(discord.SelectOption(label=m, value=m, emoji="💰"))

        if options:
            select = discord.ui.Select(placeholder="💳 Select payment method...", options=options, row=0)
            select.callback = self.payment_selected
            self.add_item(select)

        self.selected_payment = None

    async def payment_selected(self, interaction: discord.Interaction):
        self.selected_payment = interaction.data["values"][0]
        await interaction.response.send_message(
            f"✅ Payment method set to **{self.selected_payment}**. Now click **Confirm Order**!",
            ephemeral=True
        )

    @discord.ui.button(label="Confirm Order", style=discord.ButtonStyle.success, emoji="✅", row=1)
    async def confirm_btn(self, interaction: discord.Interaction, button):
        if not self.selected_payment:
            return await interaction.response.send_message(
                "❌ Please select a **payment method** first!", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)
        await create_order_channel(interaction, self.product, self.settings, self.selected_payment)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌", row=1)
    async def cancel_btn(self, interaction: discord.Interaction, button):
        await interaction.response.edit_message(
            embed=discord.Embed(title="❌ Order Cancelled", color=ERROR_COLOR),
            view=None
        )


# ═══════════════════════════════════════════════════════════════
#  CREATE ORDER CHANNEL
# ═══════════════════════════════════════════════════════════════

async def create_order_channel(interaction: discord.Interaction, product: dict,
                                settings: dict, payment_method: str):
    guild = interaction.guild
    user = interaction.user

    order_num = await increment_order_counter(guild.id)

    # Category
    cat_id = settings.get("delivery_category_id")
    category = guild.get_channel(cat_id) if cat_id else None

    # Permissions
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(
            read_messages=True, send_messages=True,
            attach_files=True, embed_links=True
        ),
        guild.me: discord.PermissionOverwrite(
            read_messages=True, send_messages=True,
            manage_channels=True, manage_messages=True
        ),
    }

    staff_role_id = settings.get("staff_role_id")
    if staff_role_id:
        role = guild.get_role(staff_role_id)
        if role:
            overwrites[role] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True,
                attach_files=True, embed_links=True, manage_messages=True
            )

    # Create channel
    channel_name = f"order-{order_num:04d}"
    try:
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Order #{order_num:04d} | {user} | {product['name']} | {payment_method}",
            reason=f"Order by {user}"
        )
    except discord.Forbidden:
        return await interaction.followup.send("❌ I can't create channels!", ephemeral=True)

    # Save order
    order_id = await create_order(
        guild.id, order_num, user.id, product["id"],
        product["name"], product["price"], channel.id
    )
    await update_order_field(order_id, "payment_method", payment_method)

    # Decrement stock
    await decrement_stock(product["id"])

    # Order embed
    embed = discord.Embed(
        title=f"🧾 Order #{order_num:04d}",
        description=(
            f"Thank you for your order, {user.mention}!\n\n"
            f"A staff member will process your order shortly."
        ),
        color=ORDER_COLOR,
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(name="📦 Product", value=f"{product['emoji']} {product['name']}", inline=True)
    embed.add_field(name="💰 Price", value=f"`${product['price']:.2f}`", inline=True)
    embed.add_field(name="💳 Payment", value=f"`{payment_method}`", inline=True)
    embed.add_field(name="⏱️ Delivery", value=f"`{product.get('delivery_time', '5M-2H')}`", inline=True)
    embed.add_field(name="📌 Status", value="🟡 `Pending`", inline=True)
    embed.add_field(name="🆔 Order ID", value=f"`{order_id}`", inline=True)

    # Clean payment method name for display (remove custom emoji codes)
    import re
    clean_payment = re.sub(r'<a?:\w+:\d+>\s*', '', payment_method).strip()

    embed.add_field(
        name="📝 Instructions",
        value=(
            f"1️⃣ Send your **{clean_payment}** payment to the address provided by staff\n"
            "2️⃣ Send **payment proof** (screenshot/TXID) in this channel\n"
            "3️⃣ Wait for staff to **verify** and **deliver**\n\n"
            "⚠️ *Do NOT close this channel until your order is delivered!*"
        ),
        inline=False
    )

    embed.set_footer(text=f"Order ID: {order_id} • Hubix Orders")
    embed.set_thumbnail(url=user.display_avatar.url)

    view = OrderControlView()
    await channel.send(content=user.mention, embed=embed, view=view)

    # Ping staff
    if staff_role_id:
        role = guild.get_role(staff_role_id)
        if role:
            ping = await channel.send(f"{role.mention} — New order from {user.mention}!")
            await ping.delete(delay=5)

    # Log
    log_ch_id = settings.get("log_channel_id")
    if log_ch_id:
        log_ch = guild.get_channel(log_ch_id)
        if log_ch:
            log_embed = discord.Embed(
                title="🛒 New Order",
                color=ORDER_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.add_field(name="🆔 Order", value=f"`#{order_num:04d}`", inline=True)
            log_embed.add_field(name="👤 Customer", value=f"{user.mention}", inline=True)
            log_embed.add_field(name="📦 Product", value=product["name"], inline=True)
            log_embed.add_field(name="💰 Price", value=f"`${product['price']:.2f}`", inline=True)
            log_embed.add_field(name="💳 Payment", value=payment_method, inline=True)
            log_embed.add_field(name="📍 Channel", value=channel.mention, inline=True)
            log_embed.set_thumbnail(url=user.display_avatar.url)
            try:
                await log_ch.send(embed=log_embed)
            except:
                pass

    await interaction.followup.send(
        embed=discord.Embed(
            title="✅ Order Created!",
            description=f"Your order channel: {channel.mention}",
            color=SUCCESS_COLOR
        ),
        ephemeral=True
    )


# ═══════════════════════════════════════════════════════════════
#  ORDER CHANNEL CONTROLS (Persistent)
# ═══════════════════════════════════════════════════════════════

class OrderControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Processing", style=discord.ButtonStyle.primary, emoji="🔵", custom_id="nexify:order:processing", row=0)
    async def processing_btn(self, interaction: discord.Interaction, button):
        order = await get_order_by_channel(interaction.channel.id)
        if not order:
            return await interaction.response.send_message("❌ Not an order channel.", ephemeral=True)
        settings = await get_shop_settings(interaction.guild.id)
        if not await self.is_staff(interaction, settings):
            return await interaction.response.send_message("❌ Staff only!", ephemeral=True)

        await update_order_status(order["id"], "processing", interaction.user.id)

        embed = discord.Embed(
            title="🔵 Order Processing",
            description=f"Order **#{order['order_number']:04d}** is now being processed by {interaction.user.mention}.",
            color=0x3498DB
        )
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="Deliver", style=discord.ButtonStyle.success, emoji="✅", custom_id="nexify:order:deliver", row=0)
    async def deliver_btn(self, interaction: discord.Interaction, button):
        order = await get_order_by_channel(interaction.channel.id)
        if not order:
            return await interaction.response.send_message("❌ Not an order channel.", ephemeral=True)
        settings = await get_shop_settings(interaction.guild.id)
        if not await self.is_staff(interaction, settings):
            return await interaction.response.send_message("❌ Staff only!", ephemeral=True)

        # Show delivery modal
        modal = DeliveryModal(order, settings)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Cancel Order", style=discord.ButtonStyle.danger, emoji="❌", custom_id="nexify:order:cancel", row=0)
    async def cancel_btn(self, interaction: discord.Interaction, button):
        order = await get_order_by_channel(interaction.channel.id)
        if not order:
            return await interaction.response.send_message("❌ Not an order channel.", ephemeral=True)

        # Owner or staff can cancel
        settings = await get_shop_settings(interaction.guild.id)
        is_staff = await self.is_staff(interaction, settings)
        is_owner = interaction.user.id == order["user_id"]

        if not is_staff and not is_owner:
            return await interaction.response.send_message("❌ Only staff or the order owner can cancel!", ephemeral=True)

        await update_order_status(order["id"], "cancelled", interaction.user.id)

        embed = discord.Embed(
            title="❌ Order Cancelled",
            description=f"Order **#{order['order_number']:04d}** has been cancelled by {interaction.user.mention}.",
            color=ERROR_COLOR
        )
        await interaction.response.send_message(embed=embed)

        # Log
        if settings and settings.get("log_channel_id"):
            log_ch = interaction.guild.get_channel(settings["log_channel_id"])
            if log_ch:
                try:
                    await log_ch.send(embed=discord.Embed(
                        title="❌ Order Cancelled",
                        description=f"**#{order['order_number']:04d}** — {order['product_name']}\nBy: {interaction.user.mention}",
                        color=ERROR_COLOR,
                        timestamp=datetime.now(timezone.utc)
                    ))
                except:
                    pass

    @discord.ui.button(label="Request Staff", style=discord.ButtonStyle.primary, emoji="🔔", custom_id="nexify:order:reqstaff", row=1)
    async def request_staff_btn(self, interaction: discord.Interaction, button):
        order = await get_order_by_channel(interaction.channel.id)
        if not order:
            return await interaction.response.send_message("❌ Not an order channel.", ephemeral=True)

        if interaction.user.id != order["user_id"]:
            return await interaction.response.send_message("❌ Only the customer can request staff!", ephemeral=True)

        # 30 minute cooldown check
        last_request = await get_last_staff_request(interaction.guild.id, interaction.user.id)
        if last_request:
            from datetime import datetime, timezone, timedelta
            try:
                last_dt = datetime.fromisoformat(last_request).replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                diff = (now - last_dt).total_seconds()
                remaining = 1800 - diff  # 30 minutes = 1800 seconds
                if remaining > 0:
                    mins = int(remaining // 60)
                    secs = int(remaining % 60)
                    return await interaction.response.send_message(
                        f"⏳ You can request staff again in **{mins}m {secs}s**.",
                        ephemeral=True
                    )
            except:
                pass

        await save_staff_request(interaction.guild.id, interaction.user.id)

        settings = await get_shop_settings(interaction.guild.id)
        staff_ping = ""
        if settings and settings.get("staff_role_id"):
            role = interaction.guild.get_role(settings["staff_role_id"])
            if role:
                staff_ping = role.mention

        embed = discord.Embed(
            title="🔔 Staff Requested!",
            description=(
                f"{interaction.user.mention} is requesting assistance for "
                f"Order **#{order['order_number']:04d}**.\n\n"
                f"📦 **Product:** {order['product_name']}\n"
                f"💰 **Price:** `${order['price']:.2f}`"
            ),
            color=WARNING_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="Staff will respond as soon as possible")

        await interaction.response.send_message(
            content=staff_ping,
            embed=embed
        )

    @discord.ui.button(label="Close Channel", style=discord.ButtonStyle.secondary, emoji="🔒", custom_id="nexify:order:close", row=1)
    async def close_btn(self, interaction: discord.Interaction, button):
        order = await get_order_by_channel(interaction.channel.id)
        if not order:
            return await interaction.response.send_message("❌ Not an order channel.", ephemeral=True)

        if order["status"] not in ("delivered", "cancelled"):
            return await interaction.response.send_message(
                "❌ Order must be delivered or cancelled before closing!",
                ephemeral=True
            )

        await interaction.response.send_message("🔒 Closing in 5 seconds...")
        await discord.utils.sleep_until(datetime.now(timezone.utc) + __import__('datetime').timedelta(seconds=5))
        try:
            await interaction.channel.delete(reason="Order completed")
        except:
            pass

    @discord.ui.button(label="Order Info", style=discord.ButtonStyle.secondary, emoji="ℹ️", custom_id="nexify:order:info", row=1)
    async def info_btn(self, interaction: discord.Interaction, button):
        order = await get_order_by_channel(interaction.channel.id)
        if not order:
            return await interaction.response.send_message("❌ Not an order.", ephemeral=True)

        status_emoji = {
            "pending": "🟡", "processing": "🔵",
            "delivered": "🟢", "cancelled": "🔴", "refunded": "🟠"
        }

        embed = discord.Embed(
            title=f"ℹ️ Order #{order['order_number']:04d}",
            color=ORDER_COLOR
        )
        embed.add_field(name="📦 Product", value=order["product_name"], inline=True)
        embed.add_field(name="💰 Price", value=f"`${order['price']:.2f}`", inline=True)
        embed.add_field(name="💳 Payment", value=order.get("payment_method", "N/A"), inline=True)
        embed.add_field(name="📌 Status", value=f"{status_emoji.get(order['status'], '⚪')} {order['status'].title()}", inline=True)
        embed.add_field(name="👤 Customer", value=f"<@{order['user_id']}>", inline=True)
        if order.get("staff_id"):
            embed.add_field(name="👷 Staff", value=f"<@{order['staff_id']}>", inline=True)
        embed.add_field(name="📅 Created", value=order["created_at"][:16], inline=True)

        if order.get("delivery_info"):
            embed.add_field(name="📬 Delivery Info", value=f"```{order['delivery_info']}```", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def is_staff(self, interaction, settings):
        if interaction.user.guild_permissions.administrator:
            return True
        if settings and settings.get("staff_role_id"):
            role = interaction.guild.get_role(settings["staff_role_id"])
            if role and role in interaction.user.roles:
                return True
        return False


# ═══════════════════════════════════════════════════════════════
#  DELIVERY MODAL
# ═══════════════════════════════════════════════════════════════

class DeliveryModal(discord.ui.Modal, title="✅ Deliver Order"):
    delivery_input = discord.ui.TextInput(
        label="Delivery Info / Product Key",
        placeholder="Paste the product details, keys, links, etc.",
        style=discord.TextStyle.paragraph,
        max_length=2000
    )
    notes_input = discord.ui.TextInput(
        label="Notes to Customer (optional)",
        placeholder="Any additional notes...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )

    def __init__(self, order, settings):
        super().__init__()
        self.order = order
        self.settings = settings

    async def on_submit(self, interaction: discord.Interaction):
        order = self.order
        delivery_info = self.delivery_input.value
        notes = self.notes_input.value if self.notes_input.value else None

        await update_order_status(order["id"], "delivered", interaction.user.id)
        await update_order_field(order["id"], "delivery_info", delivery_info)
        if notes:
            await update_order_field(order["id"], "notes", notes)

        # Update customer profile
        await update_customer_profile(interaction.guild.id, order["user_id"], order["price"])

        # Auto customer role
        if self.settings.get("auto_customer_role") and self.settings.get("customer_role_id"):
            member = interaction.guild.get_member(order["user_id"])
            role = interaction.guild.get_role(self.settings["customer_role_id"])
            if member and role:
                try:
                    await member.add_roles(role, reason="Customer role — order delivered")
                except:
                    pass

        # Delivery embed
        embed = discord.Embed(
            title="✅ Order Delivered!",
            description=f"Your order **#{order['order_number']:04d}** has been delivered!",
            color=DELIVERED_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="📦 Product", value=order["product_name"], inline=True)
        embed.add_field(name="👷 Delivered By", value=interaction.user.mention, inline=True)
        embed.add_field(
            name="📬 Delivery Details",
            value=f"```{delivery_info}```",
            inline=False
        )
        if notes:
            embed.add_field(name="📝 Notes", value=notes, inline=False)

        embed.add_field(
            name="⭐ Leave a Review!",
            value="Click the **Review** button below to rate your experience!",
            inline=False
        )

        embed.set_footer(text="Thank you for your purchase! • Hubix")

        view = PostDeliveryView(order)
        await interaction.response.send_message(
            content=f"<@{order['user_id']}>",
            embed=embed,
            view=view
        )

        # Log
        if self.settings.get("log_channel_id"):
            log_ch = interaction.guild.get_channel(self.settings["log_channel_id"])
            if log_ch:
                log_embed = discord.Embed(
                    title="✅ Order Delivered",
                    color=DELIVERED_COLOR,
                    timestamp=datetime.now(timezone.utc)
                )
                log_embed.add_field(name="🆔", value=f"`#{order['order_number']:04d}`", inline=True)
                log_embed.add_field(name="👤 Customer", value=f"<@{order['user_id']}>", inline=True)
                log_embed.add_field(name="📦 Product", value=order["product_name"], inline=True)
                log_embed.add_field(name="💰 Price", value=f"`${order['price']:.2f}`", inline=True)
                log_embed.add_field(name="👷 Staff", value=interaction.user.mention, inline=True)
                try:
                    await log_ch.send(embed=log_embed)
                except:
                    pass


class PostDeliveryView(discord.ui.View):
    def __init__(self, order):
        super().__init__(timeout=None)
        self.order = order

    @discord.ui.button(label="Leave Review", style=discord.ButtonStyle.primary, emoji="⭐")
    async def review_btn(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.order["user_id"]:
            return await interaction.response.send_message("❌ Only the customer can review!", ephemeral=True)

        plan = await get_guild_plan(interaction.guild.id)
        limits = get_plan_limits(plan)
        if not limits.get("reviews_enabled"):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="🔒 Reviews Locked",
                    description="Reviews require **⭐ Premium** plan.\nContact the bot owner!",
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )

        modal = ReviewModal(self.order)
        await interaction.response.send_modal(modal)


class ReviewModal(discord.ui.Modal, title="⭐ Leave a Review"):
    rating_input = discord.ui.TextInput(
        label="Rating (1-5 stars)",
        placeholder="5",
        max_length=1
    )
    comment_input = discord.ui.TextInput(
        label="Comment (optional)",
        placeholder="How was your experience?",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )

    def __init__(self, order):
        super().__init__()
        self.order = order

    async def on_submit(self, interaction: discord.Interaction):
        try:
            rating = int(self.rating_input.value)
            if rating < 1 or rating > 5:
                raise ValueError
        except:
            return await interaction.response.send_message("❌ Rating must be 1-5!", ephemeral=True)

        comment = self.comment_input.value or ""
        success = await add_review(
            interaction.guild.id, self.order["id"],
            interaction.user.id, rating, comment
        )

        if not success:
            return await interaction.response.send_message("❌ You already reviewed this order!", ephemeral=True)

        stars = "⭐" * rating + "☆" * (5 - rating)
        embed = discord.Embed(
            title="⭐ Review Submitted!",
            description=f"{stars}\n\n{comment}" if comment else stars,
            color=ORDER_COLOR
        )
        embed.add_field(name="📦 Product", value=self.order["product_name"], inline=True)
        embed.set_footer(text="Thank you for your feedback!")

        await interaction.response.send_message(embed=embed)

        # Send to review channel
        settings = await get_shop_settings(interaction.guild.id)
        review_ch = None
        if settings and settings.get("review_channel_id"):
            review_ch = interaction.guild.get_channel(settings["review_channel_id"])

        if review_ch:
            vouch_embed = discord.Embed(
                title=f"⭐ New Review — {stars}",
                description=comment or "*No comment*",
                color=ORDER_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            vouch_embed.add_field(name="👤 Customer", value=interaction.user.mention, inline=True)
            vouch_embed.add_field(name="📦 Product", value=self.order["product_name"], inline=True)
            vouch_embed.add_field(name="🆔 Order", value=f"`#{self.order['order_number']:04d}`", inline=True)
            vouch_embed.set_thumbnail(url=interaction.user.display_avatar.url)
            try:
                review_msg = await review_ch.send(embed=vouch_embed)
                await update_review_message_id(self.order["id"], review_msg.id)
            except:
                pass

            # Update review channel name with count
            try:
                count = await get_review_count(interaction.guild.id)
                prefix = settings.get("review_channel_name", "reviews")
                new_name = f"{prefix}-{count}"
                await review_ch.edit(name=new_name, reason="Review count updated")
            except:
                pass

        # Also log to log channel if different
        if settings and settings.get("log_channel_id"):
            log_ch = interaction.guild.get_channel(settings["log_channel_id"])
            if log_ch and (not review_ch or log_ch.id != review_ch.id):
                log_embed = discord.Embed(
                    title=f"⭐ New Review — {stars}",
                    description=f"<@{interaction.user.id}> reviewed order `#{self.order['order_number']:04d}`",
                    color=ORDER_COLOR,
                    timestamp=datetime.now(timezone.utc)
                )
                try:
                    await log_ch.send(embed=log_embed)
                except:
                    pass


# ═══════════════════════════════════════════════════════════════
#  MANAGEMENT MODALS
# ═══════════════════════════════════════════════════════════════

class ShopSetupModal(discord.ui.Modal, title="🏪 Shop Setup"):
    log_input = discord.ui.TextInput(label="Log Channel ID", placeholder="Order logs go here")
    cat_input = discord.ui.TextInput(label="Order Category ID (Discord category)", placeholder="Orders created here")
    staff_input = discord.ui.TextInput(label="Staff Role ID", placeholder="Who can manage orders")
    customer_input = discord.ui.TextInput(label="Customer Role ID (optional)", placeholder="Given after first purchase", required=False)
    review_input = discord.ui.TextInput(label="Review Channel ID (optional)", placeholder="Reviews posted here, name = counter", required=False)

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction):
        try:
            log_id = int(self.log_input.value)
            cat_id = int(self.cat_input.value)
            staff_id = int(self.staff_input.value)
        except:
            return await interaction.response.send_message("❌ Invalid IDs!", ephemeral=True)

        customer_id = None
        if self.customer_input.value:
            try:
                customer_id = int(self.customer_input.value)
            except:
                pass

        review_id = None
        if self.review_input.value:
            try:
                review_id = int(self.review_input.value)
            except:
                pass

        await create_shop_settings(interaction.guild.id)
        await update_shop_setting(interaction.guild.id, "log_channel_id", log_id)
        await update_shop_setting(interaction.guild.id, "delivery_category_id", cat_id)
        await update_shop_setting(interaction.guild.id, "staff_role_id", staff_id)
        await update_shop_setting(interaction.guild.id, "enabled", 1)

        if customer_id:
            await update_shop_setting(interaction.guild.id, "customer_role_id", customer_id)
        if review_id:
            await update_shop_setting(interaction.guild.id, "review_channel_id", review_id)
            # Set initial channel name with count
            review_ch = interaction.guild.get_channel(review_id)
            if review_ch:
                try:
                    count = await get_review_count(interaction.guild.id)
                    s = await get_shop_settings(interaction.guild.id)
                    prefix = s.get("review_channel_name", "reviews") if s else "reviews"
                    await review_ch.edit(name=f"{prefix}-{count}", reason="Review channel setup")
                except:
                    pass

        e = discord.Embed(title="✅ Shop Setup Complete!", color=SUCCESS_COLOR)
        e.add_field(name="📌 Log", value=f"<#{log_id}>", inline=True)
        e.add_field(name="📂 Category", value=f"<#{cat_id}>", inline=True)
        e.add_field(name="🏷️ Staff", value=f"<@&{staff_id}>", inline=True)
        if customer_id:
            e.add_field(name="👤 Customer Role", value=f"<@&{customer_id}>", inline=True)
        if review_id:
            e.add_field(name="⭐ Review Channel", value=f"<#{review_id}>", inline=True)
        await interaction.response.send_message(embed=e, ephemeral=True)


class AddProductModal(discord.ui.Modal, title="📦 Add Product"):
    quick_input = discord.ui.TextInput(
        label="Quick Add (paste formatted text)",
        placeholder="Name: Product Name\nDescription: Details\nPrice: 5.40\nEmoji: 🛒\nExtra: Category|5M-2H|5.00",
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True
    )

    async def on_submit(self, interaction):
        raw = self.quick_input.value.strip()

        # Parse key: value format
        parsed = {}
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                key, _, val = line.partition(":")
                parsed[key.strip().lower()] = val.strip()

        # Extract fields
        name = parsed.get("name", "").strip()
        description = parsed.get("description", "").strip()
        price_str = parsed.get("price", "0").strip()
        emoji = parsed.get("emoji", "🛒").strip()
        extra = parsed.get("extra", "").strip()

        # Validate name
        if not name:
            return await interaction.response.send_message(
                "❌ **Name** is required!\n\n"
                "**Format:**\n```\nName: Product Name\nDescription: Details\nPrice: 5.40\nEmoji: 🛒\nExtra: Category|5M-2H|5.00```",
                ephemeral=True
            )

        # Validate price
        try:
            price = float(price_str.replace("$", "").strip())
        except:
            return await interaction.response.send_message("❌ Invalid price!", ephemeral=True)

        if not emoji:
            emoji = "🛒"

        # Parse extra
        category = "General"
        delivery = "5M-2H"
        reseller = None

        if extra:
            parts = extra.split("|")
            if len(parts) >= 1 and parts[0].strip():
                category = parts[0].strip()
            if len(parts) >= 2 and parts[1].strip():
                delivery = parts[1].strip()
            if len(parts) >= 3 and parts[2].strip():
                try:
                    reseller = float(parts[2].strip().replace("$", ""))
                except:
                    pass

        # Multi product support — check for separator "---"
        products_to_add = []
        chunks = raw.split("---")

        if len(chunks) > 1:
            # Multiple products separated by ---
            for chunk in chunks:
                chunk = chunk.strip()
                if not chunk:
                    continue
                p = {}
                for line in chunk.split("\n"):
                    line = line.strip()
                    if not line or ":" not in line:
                        continue
                    key, _, val = line.partition(":")
                    p[key.strip().lower()] = val.strip()

                p_name = p.get("name", "").strip()
                p_price_str = p.get("price", "0").strip()
                p_desc = p.get("description", "").strip()
                p_emoji = p.get("emoji", "🛒").strip() or "🛒"
                p_extra = p.get("extra", "").strip()

                if not p_name:
                    continue
                try:
                    p_price = float(p_price_str.replace("$", ""))
                except:
                    continue

                p_cat = "General"
                p_del = "5M-2H"
                p_res = None
                if p_extra:
                    ep = p_extra.split("|")
                    if len(ep) >= 1 and ep[0].strip():
                        p_cat = ep[0].strip()
                    if len(ep) >= 2 and ep[1].strip():
                        p_del = ep[1].strip()
                    if len(ep) >= 3 and ep[2].strip():
                        try:
                            p_res = float(ep[2].strip().replace("$", ""))
                        except:
                            pass

                products_to_add.append({
                    "name": p_name, "desc": p_desc, "price": p_price,
                    "emoji": p_emoji, "cat": p_cat, "del": p_del, "res": p_res
                })
        else:
            # Single product
            products_to_add.append({
                "name": name, "desc": description, "price": price,
                "emoji": emoji, "cat": category, "del": delivery, "res": reseller
            })

        # Plan check — max products
        plan = await get_guild_plan(interaction.guild.id)
        limits = get_plan_limits(plan)
        current_products = await get_products(interaction.guild.id)
        max_products = limits.get("max_products", 3)
        total_after = len(current_products) + len(products_to_add)
        if total_after > max_products:
            plan_info_name = plan.title()
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="🔒 Product Limit Reached",
                    description=(
                        f"Your **{plan_info_name}** plan allows max **{max_products}** products.\n"
                        f"You currently have **{len(current_products)}** products.\n\n"
                        f"Upgrade your plan to add more!"
                    ),
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )

        # Add all products
        added = []
        for prod in products_to_add:
            pid = await add_product(
                interaction.guild.id,
                prod["name"], prod["desc"], prod["price"],
                prod["emoji"], prod["cat"], prod["del"], prod["res"]
            )
            added.append({"id": pid, **prod})

        # Build response
        if len(added) == 1:
            p = added[0]
            e = discord.Embed(title="✅ Product Added!", color=SUCCESS_COLOR)
            e.add_field(name="📦 Name", value=p["name"], inline=True)
            e.add_field(name="💰 Price", value=f"`${p['price']:.2f}`", inline=True)
            e.add_field(name="📂 Category", value=p["cat"], inline=True)
            e.add_field(name="⏱️ Delivery", value=p["del"], inline=True)
            e.add_field(name="🆔 ID", value=f"`{p['id']}`", inline=True)
            if p["res"]:
                e.add_field(name="🏷️ Reseller", value=f"`${p['res']:.2f}`", inline=True)
        else:
            desc = ""
            for p in added:
                res_text = f" *(Reseller: ${p['res']:.2f})*" if p["res"] else ""
                desc += f"`{p['id']}` {p['emoji']} **{p['name']}** — `${p['price']:.2f}`{res_text}\n"
            e = discord.Embed(
                title=f"✅ {len(added)} Products Added!",
                description=desc,
                color=SUCCESS_COLOR
            )

        await interaction.response.send_message(embed=e, ephemeral=True)


class RemoveProductModal(discord.ui.Modal, title="🗑️ Remove Product"):
    id_input = discord.ui.TextInput(label="Product ID", placeholder="From product list")

    async def on_submit(self, interaction):
        try:
            pid = int(self.id_input.value)
        except:
            return await interaction.response.send_message("❌ Invalid ID!", ephemeral=True)
        ok = await delete_product(pid)
        await interaction.response.send_message(
            embed=discord.Embed(title="✅ Removed" if ok else "❌ Not Found", color=SUCCESS_COLOR if ok else ERROR_COLOR),
            ephemeral=True
        )


class ToggleStockModal(discord.ui.Modal, title="📦 Toggle Stock"):
    id_input = discord.ui.TextInput(label="Product ID", placeholder="Toggle in_stock for this product")

    async def on_submit(self, interaction):
        try:
            pid = int(self.id_input.value)
        except:
            return await interaction.response.send_message("❌ Invalid ID!", ephemeral=True)
        result = await toggle_product_stock(pid)
        if result is False:
            return await interaction.response.send_message("❌ Product not found!", ephemeral=True)
        status = "✅ In Stock" if result else "❌ Out of Stock"
        await interaction.response.send_message(
            embed=discord.Embed(title=f"📦 Product #{pid}: {status}", color=SUCCESS_COLOR),
            ephemeral=True
        )


class SendShopPanelModal(discord.ui.Modal, title="📩 Send Shop Panel"):
    ch_input = discord.ui.TextInput(label="Channel ID", placeholder="Where to send the shop panel")

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction):
        try:
            ch_id = int(self.ch_input.value)
        except:
            return await interaction.response.send_message("❌ Invalid ID!", ephemeral=True)
        ch = interaction.guild.get_channel(ch_id)
        if not ch:
            return await interaction.response.send_message("❌ Channel not found!", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        products = await get_products(interaction.guild.id)
        settings = await get_shop_settings(interaction.guild.id)
        currency = settings.get("currency", "$") if settings else "$"
        rating_data = await get_average_rating(interaction.guild.id)
        hide_list = settings.get("hide_product_list", 0) if settings else 0

        if hide_list:
            # Show only info message
            info_msg = settings.get("shop_info_message", "Click **🛒 Order Now** to browse and purchase our products!") if settings else "Click **🛒 Order Now** to browse and purchase our products!"
            desc = ""
            if rating_data["count"] > 0:
                stars = "⭐" * round(rating_data["average"])
                desc += f"**Rating:** {stars} ({rating_data['average']}/5 from {rating_data['count']} reviews)\n\n"
            desc += info_msg
        else:
            # Build product list by category
            categories = {}
            for p in products:
                cat = p.get("category", "General")
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(p)

            desc = ""
            if rating_data["count"] > 0:
                stars = "⭐" * round(rating_data["average"])
                desc += f"**Rating:** {stars} ({rating_data['average']}/5 from {rating_data['count']} reviews)\n\n"

            for cat_name, cat_products in categories.items():
                desc += f"**━━━ {cat_name} ━━━**\n"
                for p in cat_products:
                    stock = "✅" if p["in_stock"] else "❌ OUT OF STOCK"
                    reseller = f" *(Reseller: {currency}{p['reseller_price']:.2f})*" if p.get("reseller_price") else ""
                    desc += (
                        f"{p['emoji']} **{p['name']}** — `{currency}{p['price']:.2f}`{reseller}\n"
                        f"  ⏱️ {p.get('delivery_time', '5M-2H')} | {stock}\n"
                    )
                desc += "\n"

        embed = discord.Embed(
            title="🏪 Product Shop",
            description=desc or "*No products added yet.*",
            color=PRODUCT_COLOR
        )

        if not hide_list and settings and settings.get("payment_methods"):
            pay_lines = settings["payment_methods"].strip().split("\n")
            pay_display = "\n".join([l.strip() for l in pay_lines if l.strip()])
            embed.add_field(
                name="💳 Accepted Payments",
                value=pay_display or "N/A",
                inline=False
            )

        embed.set_footer(text="Click 'Order Now' to place an order • Hubix Shop")

        view = ShopView()
        msg = await ch.send(embed=embed, view=view)

        await update_shop_setting(interaction.guild.id, "panel_channel_id", ch.id)
        await update_shop_setting(interaction.guild.id, "panel_message_id", msg.id)

        await interaction.followup.send(
            embed=discord.Embed(title="✅ Shop Panel Sent!", description=f"Sent to {ch.mention}", color=SUCCESS_COLOR),
            ephemeral=True
        )


class PaymentMethodModal(discord.ui.Modal, title="💳 Payment Methods"):
    payment_input = discord.ui.TextInput(
        label="One per line: emoji Label; (description)",
        placeholder="<:Crypto:123> Crypto; (LTC, ETH, BTC)\n<a:Paypal:456> PayPal; (F&F Only)\n💵 CashApp; (US Only)",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(self, interaction):
        methods = self.payment_input.value.strip()
        if not methods:
            return await interaction.response.send_message("❌ Cannot be empty!", ephemeral=True)

        await update_shop_setting(interaction.guild.id, "payment_methods", methods)

        lines = [l.strip() for l in methods.split("\n") if l.strip()]
        desc = "\n".join([f"• {l}" for l in lines])

        e = discord.Embed(
            title="✅ Payment Methods Updated!",
            description=desc,
            color=SUCCESS_COLOR
        )
        e.set_footer(text=f"{len(lines)} payment method(s) • Format: emoji Label; (description)")
        await interaction.response.send_message(embed=e, ephemeral=True)


class ShopInfoMessageModal(discord.ui.Modal, title="📝 Shop Info Message"):
    info_input = discord.ui.TextInput(
        label="Info Message (shown when list is hidden)",
        placeholder="Click Order Now to browse our products!\n\nWe offer boosts, nitro, and more!",
        style=discord.TextStyle.paragraph,
        max_length=2000,
        default="Click **🛒 Order Now** to browse and purchase our products!"
    )

    async def on_submit(self, interaction):
        msg = self.info_input.value.strip()
        if not msg:
            return await interaction.response.send_message("❌ Message cannot be empty!", ephemeral=True)

        await update_shop_setting(interaction.guild.id, "shop_info_message", msg)

        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ Shop Info Message Updated!",
                description=f"**Preview:**\n\n{msg}",
                color=SUCCESS_COLOR
            ),
            ephemeral=True
        )


class ReviewChannelNameModal(discord.ui.Modal, title="✏️ Review Channel Name"):
    name_input = discord.ui.TextInput(
        label="Channel Name Prefix",
        placeholder="e.g. vouches, reviews, feedback",
        max_length=50,
        default="reviews"
    )

    async def on_submit(self, interaction):
        name = self.name_input.value.strip().lower().replace(" ", "-")
        if not name:
            return await interaction.response.send_message("❌ Name cannot be empty!", ephemeral=True)

        await update_shop_setting(interaction.guild.id, "review_channel_name", name)

        # Update channel name immediately
        settings = await get_shop_settings(interaction.guild.id)
        if settings and settings.get("review_channel_id"):
            review_ch = interaction.guild.get_channel(settings["review_channel_id"])
            if review_ch:
                try:
                    count = await get_review_count(interaction.guild.id)
                    await review_ch.edit(name=f"{name}-{count}", reason="Review channel name updated")
                except:
                    pass

        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ Review Channel Name Updated!",
                description=f"Prefix set to: **{name}**\nChannel will show as: `{name}-<count>`",
                color=SUCCESS_COLOR
            ),
            ephemeral=True
        )


class DeleteReviewModal(discord.ui.Modal, title="🗑️ Delete Review"):
    review_id_input = discord.ui.TextInput(
        label="Review ID",
        placeholder="Enter the review ID to delete"
    )

    async def on_submit(self, interaction):
        try:
            review_id = int(self.review_id_input.value)
        except:
            return await interaction.response.send_message("❌ Invalid ID!", ephemeral=True)

        review = await get_review_by_id(review_id)
        if not review:
            return await interaction.response.send_message("❌ Review not found!", ephemeral=True)

        if review["guild_id"] != interaction.guild.id:
            return await interaction.response.send_message("❌ Review not found!", ephemeral=True)

        # Delete the review message from review channel
        settings = await get_shop_settings(interaction.guild.id)
        if settings and settings.get("review_channel_id") and review.get("review_message_id"):
            review_ch = interaction.guild.get_channel(settings["review_channel_id"])
            if review_ch:
                try:
                    msg = await review_ch.fetch_message(review["review_message_id"])
                    await msg.delete()
                except:
                    pass

        # Delete from database
        await delete_review(review_id)

        # Update channel name counter
        if settings and settings.get("review_channel_id"):
            review_ch = interaction.guild.get_channel(settings["review_channel_id"])
            if review_ch:
                try:
                    count = await get_review_count(interaction.guild.id)
                    prefix = settings.get("review_channel_name", "reviews")
                    await review_ch.edit(name=f"{prefix}-{count}", reason="Review deleted")
                except:
                    pass

        await interaction.response.send_message(
            embed=discord.Embed(title="✅ Review Deleted!", description=f"Review `#{review_id}` has been removed.", color=SUCCESS_COLOR),
            ephemeral=True
        )


class BlacklistModal(discord.ui.Modal, title="🚫 Blacklist Customer"):
    uid_input = discord.ui.TextInput(label="User ID", placeholder="Right-click → Copy ID")
    reason_input = discord.ui.TextInput(label="Reason", placeholder="Why?", required=False)

    async def on_submit(self, interaction):
        try:
            uid = int(self.uid_input.value)
        except:
            return await interaction.response.send_message("❌ Invalid ID!", ephemeral=True)
        reason = self.reason_input.value or "No reason"
        await blacklist_customer(interaction.guild.id, uid, reason)
        await interaction.response.send_message(
            embed=discord.Embed(title=f"🚫 <@{uid}> Blacklisted", description=f"Reason: {reason}", color=ERROR_COLOR),
            ephemeral=True
        )


# ═══════════════════════════════════════════════════════════════
#  MANAGEMENT PANEL VIEW
# ═══════════════════════════════════════════════════════════════

class OrderManagementView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog

    @discord.ui.button(label="Setup", style=discord.ButtonStyle.success, emoji="🛡️", row=0)
    async def setup_btn(self, interaction, btn):
        await interaction.response.send_modal(ShopSetupModal(self.cog))

    @discord.ui.button(label="Send Shop", style=discord.ButtonStyle.primary, emoji="📩", row=0)
    async def send_btn(self, interaction, btn):
        await interaction.response.send_modal(SendShopPanelModal(self.cog))

    @discord.ui.button(label="Enable", style=discord.ButtonStyle.success, emoji="🟢", row=0)
    async def enable_btn(self, interaction, btn):
        s = await get_shop_settings(interaction.guild.id)
        if not s:
            return await interaction.response.send_message("❌ Run Setup first!", ephemeral=True)
        await update_shop_setting(interaction.guild.id, "enabled", 1)
        await interaction.response.send_message(embed=discord.Embed(title="🟢 Shop Enabled", color=SUCCESS_COLOR), ephemeral=True)

    @discord.ui.button(label="Disable", style=discord.ButtonStyle.danger, emoji="🔴", row=0)
    async def disable_btn(self, interaction, btn):
        await update_shop_setting(interaction.guild.id, "enabled", 0)
        await interaction.response.send_message(embed=discord.Embed(title="🔴 Shop Disabled", color=ERROR_COLOR), ephemeral=True)

    @discord.ui.button(label="Add Product", style=discord.ButtonStyle.success, emoji="📦", row=1)
    async def addprod_btn(self, interaction, btn):
        await interaction.response.send_modal(AddProductModal())

    @discord.ui.button(label="Remove Product", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def rmprod_btn(self, interaction, btn):
        await interaction.response.send_modal(RemoveProductModal())

    @discord.ui.button(label="Toggle Stock", style=discord.ButtonStyle.secondary, emoji="📦", row=1)
    async def stock_btn(self, interaction, btn):
        await interaction.response.send_modal(ToggleStockModal())

    @discord.ui.button(label="Products", style=discord.ButtonStyle.secondary, emoji="📋", row=1)
    async def listprod_btn(self, interaction, btn):
        products = await get_products(interaction.guild.id)
        if not products:
            return await interaction.response.send_message(
                embed=discord.Embed(title="📋 Products", description="*No products.*", color=WARNING_COLOR),
                ephemeral=True
            )
        desc = ""
        for p in products:
            stock = "✅" if p["in_stock"] else "❌"
            desc += f"`{p['id']}` {p['emoji']} **{p['name']}** — `${p['price']:.2f}` | {stock} | {p['category']}\n"
        await interaction.response.send_message(
            embed=discord.Embed(title=f"📋 Products ({len(products)})", description=desc, color=PRODUCT_COLOR),
            ephemeral=True
        )

    @discord.ui.button(label="Orders", style=discord.ButtonStyle.primary, emoji="📊", row=2)
    async def orders_btn(self, interaction, btn):
        stats = await get_order_stats(interaction.guild.id)
        e = discord.Embed(title="📊 Order Statistics", color=ORDER_COLOR)
        e.add_field(name="📊 Total", value=f"```{stats['total']}```", inline=True)
        e.add_field(name="🟡 Pending", value=f"```{stats['pending']}```", inline=True)
        e.add_field(name="🔵 Processing", value=f"```{stats['processing']}```", inline=True)
        e.add_field(name="🟢 Delivered", value=f"```{stats['delivered']}```", inline=True)
        e.add_field(name="🔴 Cancelled", value=f"```{stats['cancelled']}```", inline=True)
        e.add_field(name="🟠 Refunded", value=f"```{stats['refunded']}```", inline=True)
        e.add_field(name="💰 Revenue", value=f"```${stats['total_revenue']:.2f}```", inline=True)

        rating = await get_average_rating(interaction.guild.id)
        stars = "⭐" * round(rating["average"]) if rating["average"] else "N/A"
        e.add_field(name="⭐ Rating", value=f"{stars} ({rating['count']})", inline=True)

        await interaction.response.send_message(embed=e, ephemeral=True)

    @discord.ui.button(label="Blacklist", style=discord.ButtonStyle.danger, emoji="🚫", row=2)
    async def bl_btn(self, interaction, btn):
        await interaction.response.send_modal(BlacklistModal())

    @discord.ui.button(label="Reviews", style=discord.ButtonStyle.secondary, emoji="⭐", row=2)
    async def reviews_btn(self, interaction, btn):
        reviews = await get_reviews(interaction.guild.id, 10)
        rating = await get_average_rating(interaction.guild.id)
        stars = "⭐" * round(rating["average"]) if rating["average"] else "No ratings"

        e = discord.Embed(
            title=f"⭐ Reviews — {stars} ({rating['average']}/5)",
            color=ORDER_COLOR
        )
        if reviews:
            for r in reviews[:10]:
                st = "⭐" * r["rating"]
                e.add_field(
                    name=f"{st} — #{r['order_number']:04d} (Review ID: {r['id']})",
                    value=f"<@{r['user_id']}>: {r['comment'] or '*No comment*'}",
                    inline=False
                )
        else:
            e.description = "*No reviews yet.*"
        await interaction.response.send_message(embed=e, ephemeral=True)

    @discord.ui.button(label="Payment Methods", style=discord.ButtonStyle.primary, emoji="💳", row=3)
    async def payment_btn(self, interaction, btn):
        await interaction.response.send_modal(PaymentMethodModal())

    @discord.ui.button(label="Delete Review", style=discord.ButtonStyle.danger, emoji="🗑️", row=3)
    async def del_review_btn(self, interaction, btn):
        await interaction.response.send_modal(DeleteReviewModal())

    @discord.ui.button(label="Review Name", style=discord.ButtonStyle.secondary, emoji="✏️", row=3)
    async def review_name_btn(self, interaction, btn):
        await interaction.response.send_modal(ReviewChannelNameModal())

    @discord.ui.button(label="Toggle List", style=discord.ButtonStyle.secondary, emoji="👁️", row=3)
    async def toggle_list_btn(self, interaction, btn):
        s = await get_shop_settings(interaction.guild.id)
        if not s:
            return await interaction.response.send_message("❌ Run Setup first!", ephemeral=True)
        current = s.get("hide_product_list", 0)
        new_val = 0 if current else 1
        await update_shop_setting(interaction.guild.id, "hide_product_list", new_val)
        status = "🙈 **Hidden** — Only info message shown" if new_val else "👁️ **Visible** — Full product list shown"
        await interaction.response.send_message(
            embed=discord.Embed(
                title="👁️ Product List Visibility",
                description=f"Product list is now: {status}\n\n*Re-send the shop panel to apply changes.*",
                color=SUCCESS_COLOR
            ),
            ephemeral=True
        )

    @discord.ui.button(label="Shop Info", style=discord.ButtonStyle.secondary, emoji="📝", row=3)
    async def shop_info_btn(self, interaction, btn):
        await interaction.response.send_modal(ShopInfoMessageModal())

    @discord.ui.button(label="Settings", style=discord.ButtonStyle.secondary, emoji="⚙️", row=4)
    async def settings_btn(self, interaction, btn):
        s = await get_shop_settings(interaction.guild.id)
        if not s:
            return await interaction.response.send_message(
                embed=discord.Embed(title="⚙️ Settings", description="*Not configured.*", color=WARNING_COLOR),
                ephemeral=True
            )
        status = "🟢 Enabled" if s["enabled"] else "🔴 Disabled"
        e = discord.Embed(title="⚙️ Shop Settings", color=ORDER_COLOR)
        e.add_field(name="Status", value=status, inline=True)
        e.add_field(name="Log", value=f"<#{s['log_channel_id']}>" if s.get("log_channel_id") else "N/A", inline=True)
        e.add_field(name="Category", value=f"<#{s['delivery_category_id']}>" if s.get("delivery_category_id") else "N/A", inline=True)
        e.add_field(name="Staff", value=f"<@&{s['staff_role_id']}>" if s.get("staff_role_id") else "N/A", inline=True)
        e.add_field(name="Customer Role", value=f"<@&{s['customer_role_id']}>" if s.get("customer_role_id") else "N/A", inline=True)
        e.add_field(name="Payments", value=s.get("payment_methods", "N/A"), inline=True)
        e.add_field(name="Review Channel", value=f"<#{s['review_channel_id']}>" if s.get("review_channel_id") else "N/A", inline=True)
        e.add_field(name="Total Orders", value=f"`{s.get('order_counter', 0)}`", inline=True)
        list_status = "🙈 Hidden" if s.get("hide_product_list", 0) else "👁️ Visible"
        e.add_field(name="Product List", value=list_status, inline=True)
        await interaction.response.send_message(embed=e, ephemeral=True)


# ═══════════════════════════════════════════════════════════════
#  ORDERS COG
# ═══════════════════════════════════════════════════════════════

class Orders(commands.Cog):
    """🛒 Order System for Hubix"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(ShopView())
        self.bot.add_view(OrderControlView())
        print("[COG] Order system loaded.")

    @app_commands.command(name="shop", description="🛒 Open the Shop Management Panel")
    @app_commands.default_permissions(manage_guild=True)
    async def shop_panel(self, interaction: discord.Interaction):
        plan = await get_guild_plan(interaction.guild.id)
        limits = get_plan_limits(plan)
        if not limits.get("shop_enabled"):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="🔒 Feature Locked",
                    description="**Shop System** requires **💎 Basic** plan or higher.\nContact the bot owner to upgrade!",
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )
        s = await get_shop_settings(interaction.guild.id)

        embed = discord.Embed(title="🛒 Shop Management Panel", color=PANEL_COLOR)

        if s and s.get("enabled"):
            stats = await get_order_stats(interaction.guild.id)
            products = await get_products(interaction.guild.id)
            rating = await get_average_rating(interaction.guild.id)

            embed.description = (
                f"**Status:** 🟢 Enabled\n"
                f"**Products:** `{len(products)}` | **Orders:** `{stats['total']}`\n"
                f"**Revenue:** `${stats['total_revenue']:.2f}` | **Rating:** {'⭐' * round(rating['average']) if rating['average'] else 'N/A'}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🛡️ **Setup** — Configure shop\n"
                "📩 **Send Shop** — Create shop panel\n"
                "📦 **Add/Remove Product** — Manage inventory\n"
                "📦 **Toggle Stock** — In/Out of stock\n"
                "📋 **Products** — View all products\n"
                "📊 **Orders** — Statistics\n"
                "🚫 **Blacklist** — Ban a customer\n"
                "⭐ **Reviews** — View reviews\n"
                "💳 **Payment Methods** — Edit payment methods\n"
                "🗑️ **Delete Review** — Remove a review\n"
                "✏️ **Review Name** — Change review channel prefix\n"
                "👁️ **Toggle List** — Show/hide product list in panel\n"
                "📝 **Shop Info** — Edit info message (when list hidden)\n"
                "⚙️ **Settings** — View config"
            )
        else:
            embed.description = (
                "Shop is **not configured** or **disabled**.\n\n"
                "Click **🛡️ Setup** to configure:\n"
                "• Set log channel for order notifications\n"
                "• Set Discord category for order channels\n"
                "• Set staff role\n"
                "• Set payment methods\n\n"
                "Then **📦 Add Product** and **📩 Send Shop Panel**!"
            )

        embed.set_footer(text="Hubix Shop • Panel expires in 5 minutes")

        view = OrderManagementView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Orders(bot))