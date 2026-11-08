(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x368 (= s_6 (_ bv7 4))))
(not $x368)))
(check-sat)
