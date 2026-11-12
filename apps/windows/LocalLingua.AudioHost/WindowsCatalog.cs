using System.Runtime.InteropServices;
static class WindowsCatalog {
    [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)]
    struct Entry {
        public uint Size,Usage,Pid; public UIntPtr Heap; public uint Module,Threads,Parent;
        public int Priority; public uint Flags;
        [MarshalAs(UnmanagedType.ByValTStr,SizeConst=260)] public string Name;
    }
    [DllImport("kernel32.dll",SetLastError=true)] static extern IntPtr CreateToolhelp32Snapshot(uint flags,uint pid);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode)] static extern bool Process32FirstW(IntPtr handle,ref Entry entry);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode)] static extern bool Process32NextW(IntPtr handle,ref Entry entry);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
    public static object[] DiscordRoots() {
        var snapshot=CreateToolhelp32Snapshot(2,0);
        if(snapshot==new IntPtr(-1))return [];
        try {
            var entries=new Dictionary<uint,uint>();
            var entry=new Entry{Size=(uint)Marshal.SizeOf<Entry>(),Name=""};
            if(Process32FirstW(snapshot,ref entry))do {
                if(string.Equals(entry.Name,"Discord.exe",StringComparison.OrdinalIgnoreCase))entries[entry.Pid]=entry.Parent;
            }while(Process32NextW(snapshot,ref entry));
            return entries.Where(x=>!entries.ContainsKey(x.Value)).Select(x=>(object)new {pid=x.Key,name="Discord"}).ToArray();
        }finally{CloseHandle(snapshot);}
    }
}
