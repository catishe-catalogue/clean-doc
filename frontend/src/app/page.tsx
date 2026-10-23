export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 bg-slate-50 text-slate-900">
      <div className="max-w-xl w-full text-center space-y-4">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
          Чистый документ
        </h1>
        <p className="text-base text-slate-600">
          B2B микро-SaaS онлайн-конвертер PDF в Word и Excel с сохранением
          верстки и соответствием 152-ФЗ.
        </p>
        <div className="inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-sm font-medium text-blue-700">
          Срез 0: Foundation готов к интеграции
        </div>
      </div>
    </main>
  );
}
