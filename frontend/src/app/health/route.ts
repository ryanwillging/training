export const dynamic = 'force-dynamic';

export async function GET() {
  const apiBase =
    process.env.API_URL || 'https://training-ryanwillgings-projects.vercel.app';

  try {
    const response = await fetch(`${apiBase}/health`, { cache: 'no-store' });
    const body = await response.text();
    return new Response(body, {
      status: response.status,
      headers: {
        'content-type': response.headers.get('content-type') || 'application/json',
      },
    });
  } catch (error) {
    return Response.json(
      { status: 'unavailable', error: 'health_proxy_failed' },
      { status: 502 }
    );
  }
}
