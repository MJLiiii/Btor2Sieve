(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_3 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x2443 (= s_3 (_ bv7 4))))
(not $x2443)))
(check-sat)
