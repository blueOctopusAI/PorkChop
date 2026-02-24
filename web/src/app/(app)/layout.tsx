import AppSidebar from "@/components/layout/AppSidebar";
import MobileNav from "@/components/layout/MobileNav";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      <AppSidebar />
      <MobileNav />
      <main className="flex-1 md:ml-60 p-4 pt-16 md:p-8 md:pt-8">
        {children}
      </main>
    </div>
  );
}
