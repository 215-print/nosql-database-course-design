<script setup lang="ts">
import { useMessageState } from '../../composables/useMessageState';
import { reactive, ref } from 'vue';
import AppIcon from '../../components/AppIcon.vue';
import PageHeader from '../../components/PageHeader.vue';
import { createShipment } from '../../api/packages';
import { useSession } from '../../composables/useSession';
import { errorText, formatAppointment } from '../../utils/format';
import type { AppointmentSlot, PackageRecord, ShipmentCreateInput } from '../../types/api';
const { user } = useSession();
const defaults = (): ShipmentCreateInput => ({
  company: '顺丰速运',
  sender_address: '',
  receiver_name: '',
  receiver_phone: '',
  receiver_address: '',
  appointment_date: '',
  appointment_slot: '',
  is_large: false,
  is_fragile: false,
  is_fresh: false,
  is_valuable: false,
});
const form = reactive(defaults());
const saving = ref(false);
const error = useMessageState('error');
const success = useMessageState('success');
const createdOrder = ref<PackageRecord>();
const appointmentSlots: AppointmentSlot[] = [
  '9：00-10：00',
  '10：00-11：00',
  '11：00-12：00',
  '14：00-15：00',
  '15：00-16：00',
  '16：00-17：00',
  '17：00-18：00',
];
const disablePastDate = (date: Date) => date.getTime() < new Date().setHours(0, 0, 0, 0);
function clearForm() {
  Object.assign(form, defaults());
  error.value = '';
  success.value = '';
  createdOrder.value = undefined;
}
async function submit() {
  if (saving.value) return;
  error.value = '';
  success.value = '';
  createdOrder.value = undefined;
  const payload = {
    ...form,
    company: form.company.trim(),
    sender_address: form.sender_address.trim(),
    receiver_name: form.receiver_name.trim(),
    receiver_phone: form.receiver_phone.trim(),
    receiver_address: form.receiver_address.trim(),
  };
  if (!user.value.id) {
    error.value = '未获取到用户信息，请重新登录';
    return;
  }
  if (
    ![
      payload.sender_address,
      payload.company,
      payload.receiver_name,
      payload.receiver_phone,
      payload.receiver_address,
    ].every(Boolean)
  ) {
    error.value = '请完整填写寄件信息';
    return;
  }
  if (!/^1\d{10}$/.test(payload.receiver_phone)) {
    error.value = '请输入正确的 11 位收件人手机号';
    return;
  }
  if (!payload.appointment_date || !payload.appointment_slot) {
    error.value = '请选择预约日期和到站时段';
    return;
  }
  const [, slotEnd] = payload.appointment_slot.split('-');
  const [hour, minute] = slotEnd.replace('：', ':').split(':');
  const appointmentEnd = new Date(
    `${payload.appointment_date}T${hour.padStart(2, '0')}:${minute}:00`
  );
  if (appointmentEnd <= new Date()) {
    error.value = '请选择尚未结束的预约时段';
    return;
  }
  saving.value = true;
  try {
    createdOrder.value = await createShipment(user.value.id, payload);
    Object.assign(form, defaults());
    success.value = '寄件订单已提交，请在预约时段内到快递站出示寄件码。';
  } catch (e) {
    error.value = errorText(e);
  } finally {
    saving.value = false;
  }
}
</script>
<template>
  <PageHeader
    title="我要寄件"
    description="填写寄收地址并预约到站时间，提交后即可获得寄件码。"
    eyebrow="校园寄件服务"
  />

  <div class="two-column">
    <section class="panel">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">填写寄件订单</h2>
          <p class="panel-description">预约到站后，工作人员将核验信息并收件入站</p>
        </div>
        <AppIcon name="send" class="muted" />
      </div>
      <form class="panel-body" @submit.prevent="submit">
        <el-alert v-if="error" class="mb-4" type="error" :title="error" :closable="false" />
        <el-alert v-if="success" class="mb-4" type="success" :title="success" :closable="false" />
        <fieldset :disabled="saving" class="m-0 min-w-0 border-0 p-0">
          <div class="form-section">
            <h3><span class="section-number">01</span>寄件与收件地址</h3>
            <div class="form-grid">
              <label class="field"
                >寄件地址<el-input
                  v-model="form.sender_address"
                  maxlength="200"
                  placeholder="填写寄件地址"
                  required
              /></label>
              <label class="field"
                >快递公司<el-input
                  v-model="form.company"
                  maxlength="50"
                  placeholder="填写寄件快递公司"
                  required
              /></label>
              <label class="field field-full"
                >详细收件地址<el-input
                  v-model="form.receiver_address"
                  type="textarea"
                  :rows="3"
                  maxlength="200"
                  placeholder="省、市、区、详细地址"
                  required
              /></label>
            </div>
            <div class="form-grid mt-4">
              <label class="field"
                >收件人姓名<el-input
                  v-model="form.receiver_name"
                  maxlength="50"
                  placeholder="输入收件人姓名"
                  required /></label
              ><label class="field"
                >收件人手机号<el-input
                  v-model="form.receiver_phone"
                  inputmode="tel"
                  maxlength="11"
                  placeholder="11 位手机号码"
                  required
              /></label>
            </div>
          </div>
          <div class="form-section">
            <h3><span class="section-number">02</span>预约到站日期和时段</h3>
            <div class="form-grid">
              <label class="field"
                >选择日期
                <el-date-picker
                  v-model="form.appointment_date"
                  type="date"
                  value-format="YYYY-MM-DD"
                  format="YYYY年MM月DD日"
                  :disabled-date="disablePastDate"
                  placeholder="选择预约日期"
                  required
                />
              </label>
              <label class="field"
                >选择时段
                <el-select v-model="form.appointment_slot" placeholder="选择到站时段" required>
                  <el-option
                    v-for="slot in appointmentSlots"
                    :key="slot"
                    :label="slot"
                    :value="slot"
                  />
                </el-select>
              </label>
            </div>
          </div>
          <div class="form-section">
            <h3><span class="section-number">03</span>包裹属性</h3>
            <div class="mt-3 flex flex-wrap gap-x-8">
              <el-checkbox v-model="form.is_large">大件物品</el-checkbox
              ><el-checkbox v-model="form.is_fragile">易碎物品</el-checkbox
              ><el-checkbox v-model="form.is_fresh">生鲜冷冻</el-checkbox
              ><el-checkbox v-model="form.is_valuable">贵重物品</el-checkbox>
            </div>
            <div class="muted mt-2 grid gap-1 text-xs">
              <p v-if="form.is_fragile">建议您使用气泡膜等防震材料妥善包装。</p>
              <p v-if="form.is_fresh">请确保已使用冰袋/泡沫箱，且请在寄件时效内送达。</p>
              <p v-if="form.is_valuable">建议您购买保价服务，以保障您的权益。</p>
            </div>
          </div>
          <div class="form-actions">
            <el-button type="primary" native-type="submit" :loading="saving"
              ><AppIcon name="send" :size="16" />提交订单</el-button
            ><el-button :disabled="saving" @click="clearForm">清空重填</el-button>
          </div>
        </fieldset>
      </form>
      <div v-if="createdOrder" class="panel-body border-line border-t">
        <el-alert type="success" :closable="false" title="订单已提交">
          <template #default>
            <p>
              预约到站：{{
                formatAppointment(
                  createdOrder.appointment_date,
                  createdOrder.appointment_slot,
                  createdOrder.appointment_at
                )
              }}
            </p>
            <p class="mt-2">请在预约时段内到快递站出示寄件码：</p>
            <strong
              class="bg-brand/5 text-brand mt-2 inline-flex rounded-lg px-4 py-2 font-mono text-2xl font-bold tracking-[0.2em]"
              >{{ createdOrder.shipment_code }}</strong
            >
          </template>
        </el-alert>
      </div>
    </section>
    <aside class="soft-note">
      <h3 class="flex items-center gap-2"><AppIcon name="box" :size="19" />寄件前准备</h3>
      <ol class="hint-list">
        <li>请填写完整地址，并核对收件人姓名和手机号。</li>
        <li>易碎物品请提前妥善包装，并勾选对应属性。</li>
        <li>提交订单后会生成寄件码，请在预约时间到站出示。</li>
        <li>工作人员核对寄件码和包裹信息后，为您收件入站。</li>
      </ol>
      <router-link class="text-link mt-4" to="/user"
        >返回我的快递<AppIcon name="arrow-right" :size="15"
      /></router-link>
    </aside>
  </div>
</template>
