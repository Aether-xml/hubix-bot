"""
Hubix Bot HTTP API — Admin panel backend
"""

from aiohttp import web
import os
import secrets
import string

API_KEY = os.getenv("API_KEY", "hubix-change-this-key")
API_PORT = int(os.getenv("PORT", os.getenv("API_PORT", "8080")))


def generate_license_key():
    chars = string.ascii_uppercase + string.digits
    parts = [''.join(secrets.choice(chars) for _ in range(4)) for _ in range(4)]
    return f"HUBIX-{'-'.join(parts)}"


class BotAPI:
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application(middlewares=[self.auth_middleware])
        self._setup_routes()

    @web.middleware
    async def auth_middleware(self, request, handler):
        if request.path == '/api/health':
            return await handler(request)

        auth = request.headers.get('Authorization', '')
        if auth != f'Bearer {API_KEY}':
            return web.json_response({'error': 'Unauthorized'}, status=401)

        return await handler(request)

    def _setup_routes(self):
        r = self.app.router
        r.add_get('/api/health', self.health)
        r.add_get('/api/stats', self.get_stats)
        r.add_get('/api/guilds', self.get_guilds)
        r.add_get('/api/subscriptions', self.get_subscriptions)
        r.add_post('/api/subscriptions/update', self.update_sub)
        r.add_post('/api/subscriptions/extend', self.extend_sub)
        r.add_post('/api/subscriptions/revoke', self.revoke_sub)
        r.add_get('/api/keys', self.get_keys)
        r.add_post('/api/keys/generate', self.gen_keys)
        r.add_post('/api/keys/delete', self.del_key)
        r.add_get('/api/logs', self.get_logs)

    async def start(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', API_PORT)
        await site.start()
        print(f"[API] Running on http://0.0.0.0:{API_PORT}")

    # ── Health ────────────────────────────────────

    async def health(self, request):
        return web.json_response({
            'status': 'ok',
            'bot': self.bot.user.name if self.bot.user else 'unknown',
            'guilds': len(self.bot.guilds),
            'latency': round(self.bot.latency * 1000),
        })

    # ── Stats ─────────────────────────────────────

    async def get_stats(self, request):
        from utils.database import get_subscription_stats, get_license_key_stats

        sub_stats = await get_subscription_stats()
        key_stats = await get_license_key_stats()
        total_users = sum(g.member_count for g in self.bot.guilds)

        return web.json_response({
            'servers': len(self.bot.guilds),
            'users': total_users,
            'latency': round(self.bot.latency * 1000),
            'subscriptions': sub_stats,
            'keys': key_stats,
        })

    # ── Guilds ────────────────────────────────────

    async def get_guilds(self, request):
        from utils.database import get_guild_plan

        guilds = []
        for g in self.bot.guilds:
            plan = await get_guild_plan(g.id)
            guilds.append({
                'id': str(g.id),
                'name': g.name,
                'members': g.member_count,
                'icon': str(g.icon.url) if g.icon else None,
                'owner_id': str(g.owner_id),
                'plan': plan,
            })

        return web.json_response({'guilds': guilds})

    # ── Subscriptions ─────────────────────────────

    async def get_subscriptions(self, request):
        from utils.database import get_all_subscriptions

        subs = await get_all_subscriptions()
        result = []
        for sub in subs:
            guild = self.bot.get_guild(sub['guild_id'])
            result.append({
                **sub,
                'guild_id': str(sub['guild_id']),
                'guild_name': guild.name if guild else 'Unknown',
                'guild_members': guild.member_count if guild else 0,
                'activated_by': str(sub['activated_by']) if sub.get('activated_by') else None,
            })

        return web.json_response({'subscriptions': result})

    async def update_sub(self, request):
        from utils.database import update_subscription_plan

        try:
            data = await request.json()
            guild_id = int(data['guild_id'])
            plan = data['plan']
            days = int(data.get('days', 30)) if data.get('days') else None
            amount = float(data.get('amount', 0))
            notes = data.get('notes', 'Updated via Admin Panel')

            await update_subscription_plan(guild_id, plan, 0, days, amount, notes)
            return web.json_response({'success': True})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=400)

    async def extend_sub(self, request):
        from utils.database import extend_subscription

        try:
            data = await request.json()
            guild_id = int(data['guild_id'])
            days = int(data['days'])
            amount = float(data.get('amount', 0))
            notes = data.get('notes', 'Extended via Admin Panel')

            result = await extend_subscription(guild_id, days, 0, amount, notes)
            if not result:
                return web.json_response({'error': 'No subscription found'}, status=404)
            return web.json_response({'success': True})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=400)

    async def revoke_sub(self, request):
        from utils.database import revoke_subscription

        try:
            data = await request.json()
            guild_id = int(data['guild_id'])
            notes = data.get('notes', 'Revoked via Admin Panel')

            await revoke_subscription(guild_id, 0, notes)
            return web.json_response({'success': True})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=400)

    # ── License Keys ──────────────────────────────

    async def get_keys(self, request):
        from utils.database import get_all_license_keys

        keys = await get_all_license_keys()
        result = []
        for k in keys:
            result.append({
                **k,
                'created_by': str(k['created_by']) if k.get('created_by') else None,
                'redeemed_by': str(k['redeemed_by']) if k.get('redeemed_by') else None,
                'redeemed_guild_id': str(k['redeemed_guild_id']) if k.get('redeemed_guild_id') else None,
            })

        return web.json_response({'keys': result})

    async def gen_keys(self, request):
        from utils.database import create_license_key

        try:
            data = await request.json()
            plan = data['plan']
            days = int(data.get('days', 30))
            count = min(int(data.get('count', 1)), 25)
            notes = data.get('notes', 'Generated via Admin Panel')

            generated = []
            for _ in range(count):
                for _attempt in range(5):
                    key = generate_license_key()
                    success = await create_license_key(key, plan, days, 0, notes)
                    if success:
                        generated.append(key)
                        break

            return web.json_response({'keys': generated, 'count': len(generated)})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=400)

    async def del_key(self, request):
        from utils.database import delete_license_key

        try:
            data = await request.json()
            key = data['key']
            result = await delete_license_key(key)
            return web.json_response({'success': result})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=400)

    # ── Logs ──────────────────────────────────────

    async def get_logs(self, request):
        from utils.database import get_subscription_logs

        limit = int(request.query.get('limit', '50'))
        logs = await get_subscription_logs(limit=limit)

        result = []
        for log in logs:
            guild = self.bot.get_guild(log['guild_id'])
            result.append({
                **log,
                'guild_id': str(log['guild_id']),
                'guild_name': guild.name if guild else 'Unknown',
                'performed_by': str(log['performed_by']),
            })

        return web.json_response({'logs': result})