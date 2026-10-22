using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Windows.Forms;

internal static class Program {
    public static string Version { get { return ((AssemblyInformationalVersionAttribute)Attribute.GetCustomAttribute(Assembly.GetExecutingAssembly(), typeof(AssemblyInformationalVersionAttribute))).InformationalVersion; } }
    [STAThread] static int Main(string[] args) {
        using (var mutex = new Mutex(false, @"Local\HELI-X-Chinese-Patch-Installer")) {
            bool owned;
            try { owned = mutex.WaitOne(0); } catch (AbandonedMutexException) { owned = true; }
            if (!owned) { if (args.Length == 0) MessageBox.Show("另一个汉化安装器正在运行，请先关闭它。"); return 1; }
            try { return MainCore(args); } finally { mutex.ReleaseMutex(); }
        }
    }
    static int MainCore(string[] args) {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        if (args.Length == 2 && args[0] == "--render-preview") {
            using (var f = new InstallerForm()) {
                f.Show(); f.Update();
                using (var b = new Bitmap(f.Width, f.Height)) { f.DrawToBitmap(b, new Rectangle(0, 0, f.Width, f.Height)); b.Save(args[1]); }
            }
            return 0;
        }
        if (args.Length > 0) {
            string command = null, root = null, log = null;
            for (int i = 0; i + 1 < args.Length; i += 2) {
                if (args[i] == "--command") command = args[i+1];
                else if (args[i] == "--helix-dir") root = args[i+1];
                else if (args[i] == "--log") log = args[i+1];
                else return 2;
            }
            if (args.Length % 2 != 0 || root == null || log == null || !ValidCommand(command)) return 2;
            try { using (var writer = new StreamWriter(log, false, new UTF8Encoding(false))) {
                object gate = new object(); return Run(command, root, delegate(string line) { lock(gate) { writer.WriteLine(line); writer.Flush(); } });
            } } catch { return 1; }
        }
        Application.Run(new InstallerForm()); return 0;
    }
    static bool ValidCommand(string c) { return c == "check" || c == "install" || c == "verify" || c == "uninstall"; }
    static string Quote(string s) { return "\"" + Regex.Replace(s, "(\\\\*)\"", "$1$1\\\"") .TrimEnd('\0') + (s.EndsWith("\\") ? new string('\\', s.Length - s.TrimEnd('\\').Length) : "") + "\""; }
    public static int Run(string command, string root, Action<string> log) {
        if (!ValidCommand(command)) throw new ArgumentException("操作无效。");
        string temp = Path.Combine(Path.GetTempPath(), "helix-zh-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(temp);
        try {
            log("准备安装工具…");
            using (var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip"))
            using (var zip = new ZipArchive(stream, ZipArchiveMode.Read)) {
                foreach (var e in zip.Entries) {
                    string target = Path.GetFullPath(Path.Combine(temp, e.FullName));
                    if (!target.StartsWith(temp + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) throw new IOException("安装包路径无效。");
                    Directory.CreateDirectory(Path.GetDirectoryName(target));
                    if (e.Name != "") e.ExtractToFile(target);
                }
            }
            var p = new Process();
            p.StartInfo = new ProcessStartInfo(Path.Combine(temp, "python.exe"), "-X utf8 " + Quote(Path.Combine(temp, "windows_patch.py")) + " " + command + " --helix-dir " + Quote(Path.GetFullPath(root)));
            p.StartInfo.WorkingDirectory = temp;
            p.StartInfo.UseShellExecute = false; p.StartInfo.CreateNoWindow = true;
            p.StartInfo.RedirectStandardOutput = true; p.StartInfo.RedirectStandardError = true;
            p.StartInfo.StandardOutputEncoding = Encoding.UTF8; p.StartInfo.StandardErrorEncoding = Encoding.UTF8;
            p.OutputDataReceived += delegate(object sender, DataReceivedEventArgs e) { if (e.Data != null) log(e.Data); };
            p.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs e) { if (e.Data != null) log(e.Data); };
            p.Start(); p.BeginOutputReadLine(); p.BeginErrorReadLine(); p.WaitForExit();
            int code = p.ExitCode; p.Dispose(); return code;
        } finally { try { Directory.Delete(temp, true); } catch { /* A scanner may briefly hold extracted runtime files. */ } }
    }
}

internal class InstallerForm : Form {
    TextBox directory = new TextBox(), output = new TextBox();
    Label status = new Label(); ProgressBar progress = new ProgressBar();
    Button browse = new Button(), install = new Button(), verify = new Button(), uninstall = new Button();
    bool busy;
    public InstallerForm() {
        Text = "HELI-X 11 简体中文补丁 · " + Program.Version;
        Font = new Font("Microsoft YaHei UI", 9F); AutoScaleMode = AutoScaleMode.Dpi;
        ClientSize = new Size(780, 530); MinimumSize = new Size(700, 540); StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(247,249,252);
        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(24), ColumnCount = 1, RowCount = 8 };
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 42)); layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 60));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 26)); layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 44));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 52)); layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 28));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100)); layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 24));
        layout.Controls.Add(new Label { Text="HELI-X 11 简体中文补丁", Font=new Font(Font.FontFamily,18F,FontStyle.Bold), Dock=DockStyle.Fill, AutoSize=false },0,0);
        layout.Controls.Add(new Label { Text="Windows x64 测试版 · 请先关闭 HELI-X\n选择已安装的 HELI-X 11 目录。安装前会检查版本并备份，卸载时保留其他设置。", Dock=DockStyle.Fill },0,1);
        layout.Controls.Add(new Label { Text="HELI-X 安装目录", Dock=DockStyle.Fill },0,2);
        var row = new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=2, RowCount=1, Margin=Padding.Empty };
        row.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100)); row.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,94));
        directory.Dock=DockStyle.Fill; directory.Margin=new Padding(0,4,10,4); directory.AccessibleName="HELI-X 安装目录";
        string candidate=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),"HELI-X11");
        if (Directory.Exists(candidate)) directory.Text=candidate;
        browse.Text="浏览…";browse.Dock=DockStyle.Fill;browse.Margin=new Padding(0,0,0,8);
        browse.Click+=delegate { using(var dlg=new FolderBrowserDialog { Description="选择包含 HELI-X 程序的安装目录", ShowNewFolderButton=false, SelectedPath=directory.Text }) if(dlg.ShowDialog(this)==DialogResult.OK) directory.Text=dlg.SelectedPath; };
        row.Controls.Add(directory,0,0);row.Controls.Add(browse,1,0);layout.Controls.Add(row,0,3);
        var actions=new FlowLayoutPanel { Dock=DockStyle.Fill, Margin=Padding.Empty, WrapContents=false };
        Button[] buttons={install,verify,uninstall};string[] titles={"安装汉化","校验补丁","卸载汉化"};string[] commands={"install","verify","uninstall"};
        for(int i=0;i<buttons.Length;i++){var b=buttons[i];string c=commands[i];b.Text=titles[i];b.Size=new Size(140,36);b.Margin=new Padding(0,4,12,4);b.Click+=delegate{Start(c);};actions.Controls.Add(b);}
        install.BackColor=Color.FromArgb(32,96,170);install.ForeColor=Color.White;install.FlatStyle=FlatStyle.Flat;
        layout.Controls.Add(actions,0,4);status.Text="请选择安装目录。";status.Dock=DockStyle.Fill;layout.Controls.Add(status,0,5);
        output.Multiline=true;output.ReadOnly=true;output.ScrollBars=ScrollBars.Vertical;output.Dock=DockStyle.Fill;output.BackColor=Color.White;output.WordWrap=true;
        output.Text="安装器可离线运行，无需另装 Python。\r\n原版程序资源保持不变；备份保存在安装目录的 .helix-zh-cn-windows 中。\r\n请选择有写入权限的目录；Program Files 目录可能需要以管理员身份运行。";
        layout.Controls.Add(output,0,6);progress.Dock=DockStyle.Fill;progress.Margin=new Padding(0,10,0,0);layout.Controls.Add(progress,0,7);Controls.Add(layout);
        FormClosing+=delegate(object sender,FormClosingEventArgs e){if(busy)e.Cancel=true;};
    }
    void Start(string command) {
        if(!Directory.Exists(directory.Text)){status.Text="目录不存在，请重新选择。";return;}
        if(command=="uninstall" && MessageBox.Show(this,"卸载中文补丁并保留备份及其他设置？","卸载汉化",MessageBoxButtons.OKCancel,MessageBoxIcon.Question)!=DialogResult.OK)return;
        busy=true;directory.Enabled=browse.Enabled=install.Enabled=verify.Enabled=uninstall.Enabled=false;
        progress.Style=ProgressBarStyle.Marquee;status.Text="正在处理，请稍候…";output.Clear();string root=directory.Text;
        var worker=new BackgroundWorker();
        worker.DoWork+=delegate(object sender,DoWorkEventArgs e){e.Result=Program.Run(command,root,delegate(string line){BeginInvoke((Action)delegate{output.AppendText(line+Environment.NewLine);});});};
        worker.RunWorkerCompleted+=delegate(object sender,RunWorkerCompletedEventArgs e){
            busy=false;directory.Enabled=browse.Enabled=install.Enabled=verify.Enabled=uninstall.Enabled=true;progress.Style=ProgressBarStyle.Blocks;
            bool ok=e.Error==null && (int)e.Result==0;status.Text=ok?"操作完成。请查看下方说明。":"操作未完成，请查看下方原因。";status.ForeColor=ok?Color.DarkGreen:Color.Firebrick;
            if(e.Error!=null)output.AppendText(e.Error.Message);worker.Dispose();
        };worker.RunWorkerAsync();
    }
}
