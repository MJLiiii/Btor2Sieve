(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x63 (= s_4 (_ bv0 4))))
(not $x63)))
(check-sat)
