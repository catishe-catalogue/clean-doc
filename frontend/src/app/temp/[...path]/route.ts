import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const filePath = params.path.join('/');
  const apiUrl =
    process.env.INTERNAL_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://localhost:8000';
  const targetUrl = `${apiUrl}/api/v1/convert/preview/temp/${filePath}`;

  try {
    const res = await fetch(targetUrl);
    if (!res.ok) {
      return new NextResponse('Превью не найдено', { status: res.status });
    }
    const contentType = res.headers.get('content-type') || 'image/jpeg';
    const blob = await res.blob();
    return new NextResponse(blob, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=3600',
      },
    });
  } catch {
    return new NextResponse('Ошибка загрузки превью', { status: 502 });
  }
}
