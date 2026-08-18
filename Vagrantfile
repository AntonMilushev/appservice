Vagrant.configure("2") do |config|
  # Име на виртуалната машина
  config.vm.define "web1" do |web|
    # Избиране на box
    web.vm.box = "ubuntu/focal64"

    # Статичен IP адрес
    web.vm.network "private_network", ip: "192.168.56.10"

    # Forward-нат порт за достъп (примерно за Nginx)
    web.vm.network "forwarded_port", guest: 80, host: 8080

    # Provisioning: обновяване на системата и инсталиране на Python и Nginx
    web.vm.provision "shell", inline: <<-SHELL
      sudo apt-get update -y
      sudo apt-get upgrade -y
      sudo apt-get install -y python3 python3-pip nginx git
    SHELL

    # Синхронизирана директория с проекта
    web.vm.synced_folder ".", "/home/vagrant/my_project"
  end
end