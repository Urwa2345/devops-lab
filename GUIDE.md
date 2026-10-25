# DevOps Lab Mid: Step-by-Step Guide

**Viva: 28 Oct 2026.** Do the steps in this order. Take a screenshot at every step marked 📸 (that's your "Docker evidence" the paper asks for).

## What the app does (TaskFlow: Flask + PostgreSQL)

- **Tasks page (`/`)**: add tasks, tick them done, delete them, filter All / Active / Done, live counters (total / pending / completed). Everything is stored in Postgres.
- **System page (`/system`)**: shows the container hostname, Python and database version, task count and DB status. Open it through the load balancer and refresh: the hostname changes between your 2 instances. Great for the viva demo.
- **`/health`**: the endpoint the load balancer uses to decide if an instance is healthy.

## What you're building

```
User -> Application Load Balancer -> 2x EC2 (Amazon Linux) -> each runs Docker Compose:
                                         [web container (Flask)] + [db container (Postgres)] + named volume
        Auto Scaling Group keeps 2 instances alive   |   Selenium tests the ALB URL
```

**Before you start:** make the app yours. Rename the app title in `app/templates/index.html` and `app.py`, change the DB name/user, rename the image. Copying another student's files = zero, and the viva will check you understand every line.

---

## Step 0: Put the project on GitHub (5 min)

The Auto Scaling instances pull your code at boot, so it must be on GitHub (public repo).

```bash
cd devops-lab
git init && git add . && git commit -m "DevOps lab"
git branch -M main
git remote add origin https://github.com/<your-username>/devops-lab.git
git push -u origin main
```

Then open `scripts/user-data.sh` and set `REPO_URL` to your repo, commit and push again.

---

## Task 2 + 3 + 4 + 5: Do these on ONE test EC2 first (Linux, Docker, Volumes, Compose)

Do all the hands-on practice on a single instance first. It's where you take most of your screenshots, and it proves everything works before the ASG.

### A. Launch a test instance
EC2 → Launch instance → **Amazon Linux 2023**, `t3.micro` (or t2.micro), create/select a key pair, security group allowing **SSH (22) from My IP** and **HTTP (80) from anywhere**. Connect with the browser (**EC2 Instance Connect**) or `ssh -i key.pem ec2-user@<public-ip>`.

### B. Task 2: Linux administration (1 mark) 📸
```bash
whoami && pwd && uname -a
cat /etc/os-release
df -h && free -h
sudo dnf update -y
mkdir -p ~/devops-lab/data
cd ~/devops-lab && touch notes.txt
echo "DevOps lab" > notes.txt && cat notes.txt
ls -l
chmod 755 data            # rwxr-xr-x
chmod 640 notes.txt       # rw-r-----
ls -l                     # show the permission change
sudo chown ec2-user:ec2-user notes.txt
```
Know this for the viva: `r=4 w=2 x=1`, so `755 = rwxr-xr-x`, `640 = rw-r-----`.

### C. Task 3: Install Docker, Dockerfile, image, container (2 marks) 📸
```bash
sudo dnf install -y docker git
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user && newgrp docker
docker --version

# Docker Compose plugin
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
docker compose version

# Get your code
git clone https://github.com/<your-username>/devops-lab.git && cd devops-lab

# Build the custom image from your Dockerfile and look at it
docker build -t devops-task-app:1.0 ./app
docker images
```
Run the web container alone to prove the image works (it will wait for a DB, so just show it starts):
```bash
docker run -d --name test_web -p 8080:5000 devops-task-app:1.0
docker ps
docker logs test_web
docker stop test_web && docker rm test_web
```

### D. Task 4: Named volume + persistence (1 mark) 📸
**Simple demo (shows the concept clearly):**
```bash
docker volume create mydata
docker volume ls
docker run --rm -v mydata:/data alpine sh -c "echo 'persist me' > /data/file.txt"   # container 1 (deleted after)
docker run --rm -v mydata:/data alpine cat /data/file.txt                           # brand-new container 2 still sees it
docker volume inspect mydata
```
**Real demo with your app (do this in Task 5 below):** add tasks, `docker compose down`, `docker compose up -d`, tasks are still there.

### E. Task 5: Docker Compose, 2 containers (2 marks) 📸
```bash
cd ~/devops-lab/devops-lab
docker compose up -d --build
docker compose ps          # shows web + db
docker volume ls           # shows devops-lab_pgdata
docker network ls
docker compose logs web
```
Open `http://<ec2-public-ip>` in the browser, add 2-3 tasks. 📸

**Persistence proof:**
```bash
docker compose down            # removes containers (NOT the volume)
docker compose up -d
```
Refresh the page: **tasks are still there**. 📸 (Never use `down -v` during the demo, it deletes the volume.)

Once this works, terminate or keep this instance, either is fine. Next you make it automatic.

---

## Task 1: Load Balancer + Auto Scaling (2 marks)

### 1. Security groups (EC2 → Security Groups)
- **alb-sg**: inbound HTTP 80 from `0.0.0.0/0`
- **app-sg**: inbound HTTP 80 **from alb-sg only**, SSH 22 from My IP

### 2. Launch Template (EC2 → Launch Templates → Create)
- Name `devops-lab-lt`, AMI **Amazon Linux 2023**, type `t3.micro`, your key pair, security group `app-sg`
- Advanced details → **User data**: paste the contents of `scripts/user-data.sh` (with your repo URL set)

### 3. Target Group (EC2 → Target Groups → Create)
- Type **Instances**, name `devops-lab-tg`, HTTP **80**
- Health check path: **`/health`**
- Create it without registering targets (the ASG does that)

### 4. Application Load Balancer (EC2 → Load Balancers → Create → ALB)
- Name `devops-lab-alb`, **Internet-facing**, pick **at least 2 Availability Zones**, security group `alb-sg`
- Listener HTTP 80 → forward to `devops-lab-tg`

### 5. Auto Scaling Group (EC2 → Auto Scaling Groups → Create)
- Name `devops-lab-asg`, launch template `devops-lab-lt`, same 2+ subnets as the ALB
- Attach to existing load balancer → choose `devops-lab-tg`
- Turn on **ELB health checks**, grace period 300 s
- Group size: **desired 2, min 2, max 3**
- Scaling policy: **Target tracking, Average CPU 50%**

Wait about 5 minutes for the instances to boot and register. 📸 (Target group showing 2 healthy targets, ASG showing 2 instances, ALB DNS name.)

### 6. Demonstrate it works
- Open `http://<ALB-DNS-name>` 📸. Refresh several times: the footer's **"Served by container"** ID changes as the ALB alternates instances.
- **Self-healing demo:** terminate one instance in EC2 → watch the ASG launch a replacement 📸 (Activity tab).

> **Heads-up (good viva answer):** each instance has its *own* database container and volume, exactly like the diagram in your paper. So data added through one instance isn't shared with the other. In production you'd use a managed DB such as RDS. Say this confidently, it shows understanding.

---

## Task 6: Selenium (2 marks)

Easiest way: run it from your **own laptop** against the ALB URL (you need Python + Chrome).

```bash
pip install selenium
cd tests
set APP_URL=http://<ALB-DNS-name>        # Windows CMD
# export APP_URL=http://<ALB-DNS-name>   # Mac/Linux
set HEADLESS=0                           # show the browser (nice for a screen recording)
python test_app.py
```
Expected output: `6/6 tests passed` and a `selenium_result.png` screenshot. 📸 (Terminal output + the screenshot.)

The 6 tests: page title, heading visible, add a task, mark a task done, container hostname shown, System page loads with the database connected.

---

## Screenshot checklist (put in a folder or one PDF as your Docker evidence)

1. Linux commands + `ls -l` before/after `chmod`
2. `docker --version`, `docker compose version`
3. `docker images` (your custom image) and `docker ps`
4. `docker volume ls` + `docker volume inspect`
5. `docker compose ps` (2 containers)
6. App in browser, then **after** `compose down/up` (data persisted)
7. Target group with 2 healthy targets, ASG, ALB DNS
8. App opened via ALB DNS, showing different container IDs
9. Selenium run output

---

## Viva cheat sheet (15 marks, be ready for these)

**EC2, ALB, ASG (3)**
- *EC2* = virtual server. *ALB* = spreads HTTP traffic across healthy instances. *ASG* = keeps the desired number of instances running and scales on a metric (CPU).
- *Why health checks?* ALB stops sending traffic to an unhealthy instance; ASG replaces it.
- *Launch template* = the blueprint (AMI, type, SG, user data) the ASG uses for new instances.
- *Why 2 AZs?* High availability: survives one data centre failing.
- *Security group* = virtual firewall. app-sg only accepts traffic from alb-sg.

**Linux (2)**
- `chmod 755`: owner rwx, group r-x, others r-x. `chown` changes owner. `ls -l` shows permissions. `sudo` = run as root.

**Docker images / Dockerfile / containers (3)**
- *Image* = read-only template; *container* = running instance of it.
- Dockerfile lines: `FROM` base image, `WORKDIR`, `COPY`, `RUN` (build time), `EXPOSE`, `CMD` (run time).
- Why copy `requirements.txt` first? Layer caching makes rebuilds faster.
- Why a non-root user? Security.

**Volumes (2)**
- Container filesystem is **ephemeral**; a named volume lives outside the container and survives removal. Postgres data is at `/var/lib/postgresql/data` → mapped to volume `pgdata`.
- `docker compose down` keeps volumes; `down -v` deletes them.
- Volume vs bind mount: volume is managed by Docker; bind mount maps a host folder.

**Compose / multi-container (3)**
- One YAML defines web + db, a shared network, and a volume, started with a single `up`.
- Containers talk via **service name as hostname** (`DB_HOST=db`) on the compose network.
- `depends_on` + `healthcheck`: the web waits until Postgres is ready.
- `ports: "80:5000"` = host port → container port.

**Selenium (2)**
- Automates a real browser. Steps: start WebDriver → open URL → locate elements (`By.ID`) → assert expected values → quit. Headless = no visible window. Explicit waits (`WebDriverWait`) avoid timing failures.

---

## After the viva: avoid AWS charges
Delete in this order: **ASG → Load Balancer → Target Group → Launch Template → any leftover instances**. The ALB costs money every hour it exists.

## Troubleshooting
- **Targets unhealthy:** wait 5 min; check `app-sg` allows port 80 from `alb-sg`; on an instance run `docker compose ps` and `cat /var/log/user-data.log`.
- **`permission denied` on docker:** run `newgrp docker` or log out and back in.
- **Instance launched but no app:** your `REPO_URL` in user data is wrong or the repo is private.
- **Selenium can't start Chrome:** install Chrome, update `pip install -U selenium`.
