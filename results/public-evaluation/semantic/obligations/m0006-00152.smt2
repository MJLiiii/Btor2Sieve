(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x325 (bvule s_4 (_ bv7 4))))
(not $x325)))
(check-sat)
