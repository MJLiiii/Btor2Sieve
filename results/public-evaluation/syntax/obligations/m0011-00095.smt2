(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x345 (bvuge s_4 (_ bv7 4))))
(not $x345)))
(check-sat)
