import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginComponent } from './pages/login/login.component';
import { UploadComponent } from './pages/upload/upload.component';
import { DashboardComponent } from './pages/dashboard/dashboard.component';
import { EvaluationDetailComponent } from './pages/evaluation-detail/evaluation-detail.component';
import { TextbooksComponent } from './pages/textbooks/textbooks.component';
import { InsightsComponent } from './pages/insights/insights.component';
import { StudyPlanPageComponent } from './pages/study-plan/study-plan.component';
import { AuthGuard } from './guards/auth.guard';

const routes: Routes = [
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'dashboard', component: DashboardComponent, canActivate: [AuthGuard] },
  { path: 'upload', component: UploadComponent, canActivate: [AuthGuard] },
  { path: 'textbooks', component: TextbooksComponent, canActivate: [AuthGuard] },
  { path: 'evaluation/:examId', component: EvaluationDetailComponent, canActivate: [AuthGuard] },
  { path: 'insights', component: InsightsComponent, canActivate: [AuthGuard] },
  { path: 'study-plan', component: StudyPlanPageComponent, canActivate: [AuthGuard] },
  { path: '**', redirectTo: 'login' },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}
