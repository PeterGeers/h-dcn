# H-DCN Backend Requirements Cleanup Script
# This script removes problematic requirements.txt files that cause boto3 version conflicts
# AWS Lambda runtime already includes boto3, so most handlers don't need it

Write-Host "🧹 Cleaning up problematic requirements.txt files..." -ForegroundColor Yellow

# List of handlers that should NOT have requirements.txt (they use shared layer or AWS runtime boto3)
$handlersToClean = @(
    "update_order_status",
    "update_cart_items", 
    "get_order_byid",
    "get_orders",
    "get_member_payments",
    "get_member_byid", 
    "get_memberships",
    "get_membership_byid",
    "get_members",
    "get_events",
    "get_event_byid",
    "get_customer_orders",
    "get_cart",
    "delete_payment",
    "delete_membership", 
    "delete_member",
    "delete_event",
    "create_payment",
    "create_order",
    "create_membership",
    "create_member",
    "create_event",
    "create_cart",
    "clear_cart",
    "update_membership"
)

$cleanedCount = 0

foreach ($handler in $handlersToClean) {
    $requirementsPath = "handler/$handler/requirements.txt"
    if (Test-Path $requirementsPath) {
        Remove-Item $requirementsPath -Force
        Write-Host "✅ Removed: $requirementsPath" -ForegroundColor Green
        $cleanedCount++
    }
}

Write-Host "🎉 Cleanup complete! Removed $cleanedCount problematic requirements.txt files" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Dependency Strategy:" -ForegroundColor Cyan
Write-Host "  ✅ Handlers with shared auth layer: No requirements.txt needed" -ForegroundColor White
Write-Host "  ✅ AWS Lambda runtime provides boto3 by default" -ForegroundColor White  
Write-Host "  ✅ Only keep requirements.txt for handlers with special dependencies:" -ForegroundColor White
Write-Host "     - hdcn_cognito_admin (needs PyJWT)" -ForegroundColor Gray
Write-Host "     - cognito_post_confirmation (needs specific boto3 version)" -ForegroundColor Gray
Write-Host ""
Write-Host "🚀 Ready for deployment!" -ForegroundColor Green