(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x522 (bvsle s_6 (_ bv0 4))))
(not $x522)))
(check-sat)
