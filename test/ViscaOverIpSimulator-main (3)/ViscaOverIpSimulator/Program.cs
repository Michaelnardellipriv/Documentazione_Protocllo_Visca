using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Tasks;
using System.Diagnostics;

namespace ViscaOverIpSimulator
{
    class Program
    {
        private const int MAX_CAMERAS = 6;
        
        // Stati correnti e target
        private static readonly int[] pan = new int[MAX_CAMERAS];
        private static readonly int[] tilt = new int[MAX_CAMERAS];
        private static readonly int[] zoom = new int[MAX_CAMERAS];
        
        private static readonly int[] targetPan = new int[MAX_CAMERAS];
        private static readonly int[] targetTilt = new int[MAX_CAMERAS];
        private static readonly int[] targetZoom = new int[MAX_CAMERAS];
        
        // Flag movimento
        private static readonly bool[] isPanning = new bool[MAX_CAMERAS];
        private static readonly bool[] isTilting = new bool[MAX_CAMERAS];
        private static readonly bool[] isZooming = new bool[MAX_CAMERAS];
        
        // Lock per thread safety
        private static readonly object[] cameraLocks = new object[MAX_CAMERAS];
        
        // Valori RAW - SINCRONIZZATI CON CLIENT
        private const int PAN_MIN = -1000;
        private const int PAN_MAX = 1000;
        private const int PAN_CENTER = 0;
        
        private const int TILT_MIN = -1000;
        private const int TILT_MAX = 1000;
        private const int TILT_CENTER = 0;
        
        private const int ZOOM_MIN = 100;
        private const int ZOOM_MAX = 400;
        private const int ZOOM_DEFAULT = 200;
        
        // SMOOTH MOVEMENT - OTTIMIZZATO PER RESPONSIVITÀ
        private const int PAN_STEP = 30;    // Bilanciato per movimento fluido ma responsivo
        private const int TILT_STEP = 30;   
        private const int ZOOM_STEP = 18;   
        
        // Update frequency - bilanciato per CPU e fluidità
        private const int UPDATE_INTERVAL_MS = 16; // ~60 FPS
        
        // Statistiche
        private static long commandsReceived = 0;
        private static long stateUpdatesSent = 0;
        private static DateTime startTime;

        static async Task Main()
        {
            const int viscaPort = 52381;
            const int rtspPort = 8554;
            
            startTime = DateTime.Now;

            // Inizializza lock
            for (int i = 0; i < MAX_CAMERAS; i++)
            {
                cameraLocks[i] = new object();
            }

            // Inizializza telecamere al centro
            InitializeCameras();
            
            PrintStartupBanner();

            var udpTask = Task.Run(() => StartUdpViscaListener(viscaPort));
            var rtspTask = Task.Run(() => StartFakeRtspServer(rtspPort));
            var smoothUpdateTask = Task.Run(() => SmoothUpdateLoop());
            var statsTask = Task.Run(() => StatisticsLoop());

            await Task.WhenAll(udpTask, rtspTask, smoothUpdateTask, statsTask);
        }

        static void InitializeCameras()
        {
            for (int i = 0; i < MAX_CAMERAS; i++)
            {
                lock (cameraLocks[i])
                {
                    pan[i] = PAN_CENTER;
                    tilt[i] = TILT_CENTER;
                    zoom[i] = ZOOM_DEFAULT;
                    
                    targetPan[i] = PAN_CENTER;
                    targetTilt[i] = TILT_CENTER;
                    targetZoom[i] = ZOOM_DEFAULT;
                    
                    isPanning[i] = false;
                    isTilting[i] = false;
                    isZooming[i] = false;
                }
            }
        }

        static void PrintStartupBanner()
        {
            Console.ForegroundColor = ConsoleColor.Cyan;
            Console.WriteLine("╔═══════════════════════════════════════════════════════════════╗");
            Console.WriteLine("║      VISCA BACKEND - OPTIMIZED SMOOTH MOVEMENT v2.0          ║");
            Console.WriteLine("╚═══════════════════════════════════════════════════════════════╝");
            Console.WriteLine();
            Console.ForegroundColor = ConsoleColor.White;
            Console.WriteLine($"  Movement Parameters:");
            Console.WriteLine($"    Pan Step:    {PAN_STEP} units/frame");
            Console.WriteLine($"    Tilt Step:   {TILT_STEP} units/frame");
            Console.WriteLine($"    Zoom Step:   {ZOOM_STEP} units/frame");
            Console.WriteLine($"    Update Rate: {1000 / UPDATE_INTERVAL_MS} FPS (~{UPDATE_INTERVAL_MS}ms)");
            Console.WriteLine();
            Console.WriteLine($"  Value Ranges:");
            Console.WriteLine($"    Pan:  {PAN_MIN} to {PAN_MAX} (center: {PAN_CENTER})");
            Console.WriteLine($"    Tilt: {TILT_MIN} to {TILT_MAX} (center: {TILT_CENTER})");
            Console.WriteLine($"    Zoom: {ZOOM_MIN} to {ZOOM_MAX} (default: {ZOOM_DEFAULT})");
            Console.WriteLine();
            Console.WriteLine($"  Network:");
            Console.WriteLine($"    VISCA Port: 52381 (UDP)");
            Console.WriteLine($"    RTSP Port:  8554 (TCP, fake)");
            Console.WriteLine($"    Cameras:    1-{MAX_CAMERAS} (independent)");
            Console.WriteLine();
            Console.ForegroundColor = ConsoleColor.Green;
            Console.WriteLine("  Server READY - Waiting for connections...");
            Console.ResetColor();
            Console.WriteLine("╚═══════════════════════════════════════════════════════════════╝\n");
        }

        static async Task SmoothUpdateLoop()
        {
            var stopwatch = Stopwatch.StartNew();
            long frameCount = 0;
            
            while (true)
            {
                frameCount++;
                
                for (int camId = 0; camId < MAX_CAMERAS; camId++)
                {
                    bool updated = false;
                    
                    lock (cameraLocks[camId])
                    {
                        // Smooth pan movement
                        if (isPanning[camId])
                        {
                            int diff = targetPan[camId] - pan[camId];
                            if (Math.Abs(diff) > 0)
                            {
                                int step = Math.Sign(diff) * Math.Min(Math.Abs(diff), PAN_STEP);
                                pan[camId] += step;
                                pan[camId] = Math.Clamp(pan[camId], PAN_MIN, PAN_MAX);
                                updated = true;
                            }
                            else
                            {
                                isPanning[camId] = false; // Raggiunto target
                            }
                        }
                        
                        // Smooth tilt movement
                        if (isTilting[camId])
                        {
                            int diff = targetTilt[camId] - tilt[camId];
                            if (Math.Abs(diff) > 0)
                            {
                                int step = Math.Sign(diff) * Math.Min(Math.Abs(diff), TILT_STEP);
                                tilt[camId] += step;
                                tilt[camId] = Math.Clamp(tilt[camId], TILT_MIN, TILT_MAX);
                                updated = true;
                            }
                            else
                            {
                                isTilting[camId] = false;
                            }
                        }
                        
                        // Smooth zoom movement
                        if (isZooming[camId])
                        {
                            int diff = targetZoom[camId] - zoom[camId];
                            if (Math.Abs(diff) > 0)
                            {
                                int step = Math.Sign(diff) * Math.Min(Math.Abs(diff), ZOOM_STEP);
                                zoom[camId] += step;
                                zoom[camId] = Math.Clamp(zoom[camId], ZOOM_MIN, ZOOM_MAX);
                                updated = true;
                            }
                            else
                            {
                                isZooming[camId] = false;
                            }
                        }
                    }
                }
                
                await Task.Delay(UPDATE_INTERVAL_MS);
            }
        }

        static void StartUdpViscaListener(int port)
        {
            using var udpServer = new UdpClient(new IPEndPoint(IPAddress.Any, port));
            
            Console.ForegroundColor = ConsoleColor.Green;
            Console.WriteLine($"[UDP] VISCA listener started on port {port}");
            Console.ResetColor();
            
            while (true)
{
    try
    {
        IPEndPoint remoteEndPoint = new(IPAddress.Any, 0);
        // 1. Ricevi il primo pacchetto disponibile
        byte[] data = udpServer.Receive(ref remoteEndPoint);

        // 2. SVUOTA IL BUFFER: se ci sono altri pacchetti accumulati, 
        // scartali tutti e tieni solo l'ultimo (il più recente)
        while (udpServer.Available > 0)
        {
            data = udpServer.Receive(ref remoteEndPoint);
        }

        Interlocked.Increment(ref commandsReceived);
        int camId = ExtractCameraId(data);
        
        // 3. Processa DIRETTAMENTE (senza Task.Run) per evitare sovrapposizioni di thread
        ProcessCommand(camId, data, remoteEndPoint, udpServer);
    }
    catch (Exception ex) { LogError(ex.Message); }
}
        }

        static int ExtractCameraId(byte[] data)
        {
            int start = 0;
            
            // Skip VISCA over IP header se presente
            if (data.Length > 8 && data[0] == 0x01 && data[1] == 0x00)
            {
                start = 8;
            }
            
            if (data.Length > start)
            {
                byte cmdByte = data[start];
                int cameraId = (cmdByte & 0x0F) - 1;
                
                if (cameraId >= 0 && cameraId < MAX_CAMERAS)
                {
                    return cameraId;
                }
            }
            
            return 0; // Default a camera 0
        }

        static void ProcessCommand(int camId, byte[] data, IPEndPoint remoteEndPoint, UdpClient udpServer)
        {
            try
            {
                int start = 0;
                if (data.Length > 8 && data[0] == 0x01)
                {
                    start = 8;
                }

                if (data.Length < start + 4)
                {
                    SendAckResponse(udpServer, remoteEndPoint, camId);
                    return;
                }

                byte cmd1 = data[start + 1];
                byte cmd2 = data[start + 2];
                byte cmd3 = data[start + 3];

                bool commandProcessed = false;

                // PAN/TILT COMMAND
                if (cmd1 == 0x06 && cmd2 == 0x01 && cmd3 == 0x05)
                {
                    if (data.Length >= start + 7)
                    {
                        byte panCmd = data[start + 5];
                        byte tiltCmd = data[start + 6];

                        lock (cameraLocks[camId])
                        {
                            // PAN Movement
                            if (panCmd == 0x01) // LEFT
                            {
                                isPanning[camId] = true;
                                targetPan[camId] = PAN_MIN;
                            }
                            else if (panCmd == 0x02) // RIGHT
                            {
                                isPanning[camId] = true;
                                targetPan[camId] = PAN_MAX;
                            }
                            else if (panCmd == 0x03) // STOP
                            {
                                lock(cameraLocks[camId]) {
        isPanning[camId] = false;
        // CRITICO: Imposta il target alla posizione ATTUALE raggiunta
        // Se non lo fai, il loop di interpolazione potrebbe riportarlo a 0 o al vecchio target
        targetPan[camId] = pan[camId]; 
    }
                            }

                            // TILT Movement
                            if (tiltCmd == 0x01) // UP
                            {
                                isTilting[camId] = true;
                                targetTilt[camId] = TILT_MAX;
                            }
                            else if (tiltCmd == 0x02) // DOWN
                            {
                                isTilting[camId] = true;
                                targetTilt[camId] = TILT_MIN;
                            }
                            else if (tiltCmd == 0x03) // STOP
                            {
                                isTilting[camId] = false;
                                targetTilt[camId] = tilt[camId];
                            }
                        }
                        
                        commandProcessed = true;
                    }
                }
                // ZOOM COMMAND
                else if (cmd1 == 0x04 && cmd2 == 0x07)
                {
                    if (data.Length >= start + 4)
                    {
                        byte zoomCmd = data[start + 3];
                        
                        lock (cameraLocks[camId])
                        {
                            if (zoomCmd == 0x02) // ZOOM IN
                            {
                                isZooming[camId] = true;
                                targetZoom[camId] = ZOOM_MAX;
                            }
                            else if (zoomCmd == 0x03) // ZOOM OUT
                            {
                                isZooming[camId] = true;
                                targetZoom[camId] = ZOOM_MIN;
                            }
                            else if (zoomCmd == 0x00) // STOP
                            {
                                isZooming[camId] = false;
                                targetZoom[camId] = zoom[camId];
                            }
                        }
                        
                        commandProcessed = true;
                    }
                }
                // INQUIRY COMMAND
                else if (cmd1 == 0x09)
                {
                    SendRawStatus(udpServer, remoteEndPoint, camId);
                    return; // No ACK for inquiry
                }

                // Invia stato e ACK
                SendRawStatus(udpServer, remoteEndPoint, camId);
                SendAckResponse(udpServer, remoteEndPoint, camId);
                
            }
            catch (Exception ex)
            {
                LogError($"Process command error: {ex.Message}");
            }
        }

        static void SendRawStatus(UdpClient udpServer, IPEndPoint remoteEndPoint, int camId)
        {
            try
            {
                int panValue, tiltValue, zoomValue;
                
                lock (cameraLocks[camId])
                {
                    panValue = pan[camId];
                    tiltValue = tilt[camId];
                    zoomValue = zoom[camId];
                }
                
                // Converti a formato wire (0-2000 per pan/tilt)
                ushort panWire = (ushort)(panValue + 1000);
                ushort tiltWire = (ushort)(tiltValue + 1000);
                ushort zoomWire = (ushort)zoomValue;
                
                byte[] response = new byte[] {
                    0x91,
                    (byte)(0x80 | (camId + 1)),
                    (byte)(panWire >> 8),
                    (byte)panWire,
                    (byte)(tiltWire >> 8),
                    (byte)tiltWire,
                    (byte)(zoomWire >> 8),
                    (byte)zoomWire,
                    0xFF
                };
                
                udpServer.Send(response, response.Length, remoteEndPoint);
                Interlocked.Increment(ref stateUpdatesSent);
            }
            catch (Exception ex)
            {
                LogError($"Send status error: {ex.Message}");
            }
        }

        static void SendAckResponse(UdpClient udpServer, IPEndPoint remoteEndPoint, int camId)
        {
            try
            {
                byte[] response = new byte[] {
                    0x90,
                    (byte)(0x80 | (camId + 1)),
                    0x00,
                    0xFF
                };
                
                udpServer.Send(response, response.Length, remoteEndPoint);
            }
            catch (Exception ex)
            {
                LogError($"Send ACK error: {ex.Message}");
            }
        }

        static async Task StatisticsLoop()
        {
            while (true)
            {
                await Task.Delay(10000); // Ogni 10 secondi
                
                var uptime = DateTime.Now - startTime;
                long cmdCount = Interlocked.Read(ref commandsReceived);
                long updateCount = Interlocked.Read(ref stateUpdatesSent);
                
                Console.ForegroundColor = ConsoleColor.Cyan;
                Console.WriteLine($"\n[STATS] Uptime: {uptime:hh\\:mm\\:ss} | Commands: {cmdCount} | Updates: {updateCount}");
                Console.ResetColor();
            }
        }

        static void StartFakeRtspServer(int port)
        {
            try
            {
                using var listener = new TcpListener(IPAddress.Any, port);
                listener.Start();
                
                Console.ForegroundColor = ConsoleColor.Yellow;
                Console.WriteLine($"[RTSP] Fake server started on port {port}");
                Console.ResetColor();
                
                while (true)
                {
                    var client = listener.AcceptTcpClient();
                    Task.Run(() => 
                    { 
                        using (client) 
                        { 
                            Thread.Sleep(5000); 
                        } 
                    });
                }
            }
            catch (Exception ex)
            {
                LogError($"RTSP server error: {ex.Message}");
            }
        }

        static void LogError(string message)
        {
            Console.ForegroundColor = ConsoleColor.Red;
            Console.WriteLine($"[ERROR {DateTime.Now:HH:mm:ss}] {message}");
            Console.ResetColor();
        }
    }
}