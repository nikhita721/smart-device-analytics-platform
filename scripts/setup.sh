#!/bin/bash

# IoT Data Engineering Project Setup Script
# This script sets up the complete data engineering environment

set -e

echo "🚀 Setting up IoT Data Engineering Project..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    print_status "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
}

# Check if Python is installed
check_python() {
    print_status "Checking Python installation..."
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.9+ first."
        exit 1
    fi
    
    # Check Python version
    python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if [[ $(echo "$python_version < 3.9" | bc -l) -eq 1 ]]; then
        print_error "Python 3.9+ is required. Current version: $python_version"
        exit 1
    fi
    
    print_success "Python $python_version is installed"
}

# Create necessary directories
create_directories() {
    print_status "Creating project directories..."
    
    directories=(
        "data/raw"
        "data/processed"
        "data/models"
        "logs"
        "notebooks"
        "tests"
        "docs"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        print_status "Created directory: $dir"
    done
    
    print_success "Project directories created"
}

# Install Python dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt
        print_success "Python dependencies installed"
    else
        print_warning "requirements.txt not found, skipping Python dependency installation"
    fi
}

# Set up environment variables
setup_environment() {
    print_status "Setting up environment variables..."
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        cat > .env << EOF
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=iot-device-data

# AWS Configuration (replace with your values)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET=your-iot-data-bucket

# Database Configuration
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=airflow

# MLflow Configuration
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_DEFAULT_ARTIFACT_ROOT=s3://your-iot-data-bucket/mlflow

# Dashboard Configuration
DASHBOARD_PORT=8501
DASHBOARD_HOST=0.0.0.0
EOF
        print_success "Environment file created: .env"
        print_warning "Please update the .env file with your actual configuration values"
    else
        print_status "Environment file already exists"
    fi
}

# Build Docker images
build_docker_images() {
    print_status "Building Docker images..."
    
    # Build Airflow image
    print_status "Building Airflow image..."
    docker build -f infrastructure/Dockerfile.airflow -t iot-airflow:latest .
    
    # Build Dashboard image
    print_status "Building Dashboard image..."
    docker build -f infrastructure/Dockerfile.dashboard -t iot-dashboard:latest .
    
    print_success "Docker images built successfully"
}

# Start services
start_services() {
    print_status "Starting services with Docker Compose..."
    
    # Start services in background
    docker-compose up -d
    
    print_success "Services started successfully"
    print_status "Waiting for services to be ready..."
    
    # Wait for services to be ready
    sleep 30
    
    print_success "All services are ready!"
}

# Display service URLs
show_service_urls() {
    print_success "🎉 IoT Data Engineering Project is ready!"
    echo ""
    echo "📊 Service URLs:"
    echo "  • Airflow Web UI: http://localhost:8080 (admin/admin)"
    echo "  • Streamlit Dashboard: http://localhost:8501"
    echo "  • Jupyter Notebook: http://localhost:8888"
    echo "  • MLflow UI: http://localhost:5000"
    echo "  • Kafka: localhost:9092"
    echo "  • PostgreSQL: localhost:5432"
    echo ""
    echo "📁 Project Structure:"
    echo "  • Data Ingestion: ./data_ingestion/"
    echo "  • Data Processing: ./data_processing/"
    echo "  • ML Ops: ./ml_ops/"
    echo "  • Orchestration: ./orchestration/"
    echo "  • Monitoring: ./monitoring/"
    echo "  • Infrastructure: ./infrastructure/"
    echo ""
    echo "🚀 Next Steps:"
    echo "  1. Update configuration in .env file"
    echo "  2. Start data ingestion: python data_ingestion/kafka_producer.py"
    echo "  3. Monitor pipeline in Airflow UI"
    echo "  4. View analytics in Streamlit dashboard"
    echo ""
    echo "📚 Documentation:"
    echo "  • README.md - Project overview and setup"
    echo "  • docs/ - Technical documentation"
    echo "  • notebooks/ - Jupyter notebooks for development"
}

# Main setup function
main() {
    echo "🏠 IoT Data Engineering Project Setup"
    echo "======================================"
    echo ""
    
    # Check prerequisites
    check_docker
    check_python
    
    # Setup project
    create_directories
    install_dependencies
    setup_environment
    build_docker_images
    start_services
    
    # Show results
    show_service_urls
}

# Run main function
main "$@"
